import os
import time
import random
import requests
import urllib.parse
import asyncio
import edge_tts
import google.generativeai as genai

# Impor MoviePy 2.0 beserta modul Efek Volume-nya
from moviepy import AudioFileClip, CompositeAudioClip, CompositeVideoClip, ColorClip, ImageClip, concatenate_videoclips, concatenate_audioclips
from moviepy.audio.fx import MultiplyVolume
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.abspath(os.getcwd())

# Konfigurasi Google AI Studio (Gemini API)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# 1. GEMINI AI: GENERATOR AYAT & RENUNGAN
# ==========================================
def generate_bible_content(num_videos=5):
    print(f"🕊️ Memohon hikmat Gemini AI untuk meracik {num_videos} renungan Firman Tuhan...")
    
    prompt = f"""
    Bertindaklah sebagai Pendeta dan konten kreator rohani Kristen yang penuh karisma. 
    Buatlah {num_videos} naskah video pendek (Reels) berdasarkan ayat Alkitab dalam Bahasa Indonesia.
    Gunakan pemisah '---' antar naskah. Format persis seperti ini:
    
    AYAT: [Kutipan ayat Alkitab, misal: "Tuhan adalah gembalaku, takkan kekurangan aku." - Mazmur 23:1]
    RENUNGAN: [Renungan singkat yang sangat mendalam, menyentuh hati, dan menguatkan iman. Panjang 2-3 kalimat]
    CTA: [Ajakan interaksi, misal: Ketik "Amin" jika kamu percaya janji Tuhan!]
    PROMPT_GAMBAR: [Deskripsi bahasa Inggris untuk AI Gambar. Harus berisi: Cinematic portrait of Jesus Christ, highly detailed, photorealistic, cinematic lighting, 8k, divine atmosphere, holy light, [tambahkan detail latar sesuai ayat]]
    """
    
    model = genai.GenerativeModel('gemini-3.5-flash')
    
    raw_text = ""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            raw_text = response.text
            break 
        except Exception as e:
            print(f"⚠️ Error dari Google (Percobaan {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(65)
            else:
                raise Exception(f"❌ Gagal total menghubungi Gemini AI: {e}")

    batch = []
    for i, chunk in enumerate(raw_text.split("---")):
        if i >= num_videos: break
        lines = [line.strip() for line in chunk.strip().split("\n") if line.strip()]
        if not lines: continue
        
        ayat, renungan, cta, prompt_gbr = "Yohanes 3:16", "Kasih Tuhan tanpa batas.", "Ketik Amin!", "Cinematic Jesus Christ, divine light, 8k"
        for line in lines:
            if line.startswith("AYAT:"): ayat = line.replace("AYAT:", "").strip()
            elif line.startswith("RENUNGAN:"): renungan = line.replace("RENUNGAN:", "").strip()
            elif line.startswith("CTA:"): cta = line.replace("CTA:", "").strip()
            elif line.startswith("PROMPT_GAMBAR:"): prompt_gbr = line.replace("PROMPT_GAMBAR:", "").strip()
                
        batch.append({
            "id": f"BIBLE_{int(time.time())}_{i}",
            "ayat": ayat,
            "renungan": renungan,
            "cta": cta,
            "prompt_gambar": prompt_gbr
        })
    print(f"✅ Berhasil meracik {len(batch)} Naskah Firman Tuhan!")
    return batch

# ==========================================
# 2. POLLINATIONS AI: GENERATOR GAMBAR YESUS
# ==========================================
def generate_cinematic_jesus(prompt, output_filename):
    print(f"🎨 Melukis visual sinematik: '{prompt[:50]}...'")
    full_prompt = f"{prompt}, vertical 9:16 aspect ratio, dramatic lighting, masterpiece, trending on artstation"
    encoded_prompt = urllib.parse.quote(full_prompt)
    seed = random.randint(1, 999999)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true&seed={seed}"
    
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_filename, 'wb') as f:
            f.write(response.content)
        return output_filename
    raise Exception("Gagal menghasilkan gambar dari AI.")

# ==========================================
# 3. EDGE-TTS NATIVE (SUARA BERWIBAWA)
# ==========================================
async def _generate_audio_async(text, output_audio):
    communicate = edge_tts.Communicate(text, "id-ID-ArdiNeural", rate="-5%")
    await communicate.save(output_audio)

def generate_edge_tts_voice(text, output_audio):
    print("🎙️ Merekam suara narator berwibawa (Edge-TTS Native)...")
    asyncio.run(_generate_audio_async(text, output_audio))
    if not os.path.exists(output_audio) or os.path.getsize(output_audio) == 0:
        raise Exception(f"File audio {output_audio} gagal dibuat!")
    return output_audio

# ==========================================
# 4. TEKS ESTETIK (STATIC + TYPEWRITER)
# ==========================================
def get_custom_font():
    font_filename = os.path.join(BASE_DIR, "Montserrat-Black.ttf")
    if not os.path.exists(font_filename) or os.path.getsize(font_filename) < 100000:
        print("📥 Mengunduh Font Estetik...")
        url = "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Black.ttf"
        r = requests.get(url)
        with open(font_filename, 'wb') as f:
            f.write(r.content)
    return font_filename

def wrap_text_safe(text, font, draw, max_w):
    """Fungsi pembantu yang aman untuk memotong teks (Mendukung Pillow lawas & baru)"""
    words = text.split()
    lines, curr = [], ""
    for w in words:
        test = f"{curr} {w}".strip()
        
        # Perhitungan lebar teks yang aman dari error
        try:
            w_test = draw.textlength(test, font=font)
        except AttributeError:
            w_test = draw.textbbox((0,0), test, font=font)[2]
            
        if w_test <= max_w: 
            curr = test
        else: 
            if curr: lines.append(curr)
            curr = w
    if curr: lines.append(curr)
    return lines

def create_static_verse(item, output_path, img_size=(1080, 1920)):
    """Membuat Ayat Alkitab yang diam (statis) dengan SAFE ZONE yang agresif"""
    img = Image.new("RGBA", img_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # PERBAIKAN 1: Ukuran font Ayat diperkecil drastis ke 40 agar lebih fleksibel
    font = ImageFont.truetype(get_custom_font(), 40)
    
    # PERBAIKAN 2: SAFE ZONE AGRESIF (Margin kiri-kanan masing-masing 180px!)
    # Ini memastikan teks dijamin tidak terpotong lagi.
    max_w = img_size[0] - 360 
    
    lines = wrap_text_safe(item['ayat'], font, draw, max_w)
    
    # PERBAIKAN 3: Posisi Y diturunkan sedikit agar tidak tertutup Phone UI atas
    y = 280 
    
    for line in lines:
        try:
            w = draw.textlength(line, font=font)
        except AttributeError:
            w = draw.textbbox((0,0), line, font=font)[2]
            
        x = (img_size[0] - w) // 2
        for ax, ay in [(-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,2),(-2,2),(2,-2)]:
            draw.text((x+ax, y+ay), line, font=font, fill="black")
        draw.text((x, y), line, font=font, fill="gold")
        y += font.size + 15
        
    img.save(output_path)
    return output_path

def create_typewriter_subtitles(text, audio_duration, img_size=(1080, 1920)):
    """Membuat efek Typewriter Subtitle (muncul kata per kata) mengikuti audio"""
    print("📝 Menggambar frame Typewriter Dinamis...")
    
    # PERBAIKAN 4: Font Renungan juga disesuaikan ke Safe Zone yang lebih ketat
    font = ImageFont.truetype(get_custom_font(), 48)
    max_w = img_size[0] - 280 # Reels padding (140px per sisi)
    
    words = text.split()
    if not words: return None
    
    # Kelompokkan teks per 5 kata
    chunk_size = 5
    chunks = [words[i:i+chunk_size] for i in range(0, len(words), chunk_size)]
    
    time_per_word = audio_duration / len(words)
    clips = []
    
    for i, chunk_words in enumerate(chunks):
        for j in range(1, len(chunk_words) + 1):
            current_text = " ".join(chunk_words[:j])
            
            img = Image.new("RGBA", img_size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            current_lines = wrap_text_safe(current_text, font, draw, max_w)
            
            total_h = len(current_lines) * (font.size + 15)
            y = 1100 - (total_h // 2)
            
            for line in current_lines:
                try:
                    w = draw.textlength(line, font=font)
                except AttributeError:
                    w = draw.textbbox((0,0), line, font=font)[2]
                    
                x = (img_size[0] - w) // 2
                for ax, ay in [(-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,2),(-2,2),(2,-2)]:
                    draw.text((x+ax, y+ay), line, font=font, fill="black")
                draw.text((x, y), line, font=font, fill="white")
                y += font.size + 15
                
            temp_path = os.path.join(BASE_DIR, f"temp_sub_{i}_{j}.png")
            img.save(temp_path)
            
            clip = ImageClip(temp_path).with_duration(time_per_word)
            clips.append(clip)
            
    if clips:
        return concatenate_videoclips(clips)
    return None

# ==========================================
# 5. EDITOR VIDEO (MIX AUDIO + BGM + GAMBAR)
# ==========================================
def render_bible_video(img_bg_path, voice_path, item, output_video):
    print("🎬 Merakit Video Firman Tuhan...")
    voice_clip = AudioFileClip(voice_path)
    video_duration = voice_clip.duration + 2.0 
    
    # --- AUDIO MIXING ---
    bgm_file = os.path.join(BASE_DIR, "bgm.mp3")
    final_audio = voice_clip 
    
    if os.path.exists(bgm_file):
        print("   -> Menambahkan musik latar surgawi (BGM)...")
        bgm_clip = AudioFileClip(bgm_file).with_effects([MultiplyVolume(0.12)])
        if bgm_clip.duration < video_duration:
            n_loops = int(video_duration // bgm_clip.duration) + 1
            bgm_clip = concatenate_audioclips([bgm_clip] * n_loops)
        bgm_clip = bgm_clip.subclipped(0, video_duration)
        final_audio = CompositeAudioClip([bgm_clip, voice_clip.with_start(0.5)])
    
    # --- VISUAL MIXING ---
    visual_clip = ImageClip(img_bg_path).with_duration(video_duration)
    overlay = ColorClip(size=(1080, 1920), color=(0,0,0)).with_opacity(0.55).with_duration(video_duration)
    
    # 1. Ayat Statis (Diam di atas, SEKARANG AMAN)
    verse_path = create_static_verse(item, os.path.join(BASE_DIR, "verse_temp.png"))
    verse_clip = ImageClip(verse_path).with_duration(video_duration)
    
    video_layers = [visual_clip, overlay, verse_clip]
    
    # 2. Efek Typewriter (Renungan & CTA)
    text_to_type = f"{item['renungan']} 🙏 {item['cta']}"
    subs_clip = create_typewriter_subtitles(text_to_type, voice_clip.duration)
    
    if subs_clip:
        subs_clip = subs_clip.with_start(0.5) 
        video_layers.append(subs_clip)
    
    video = CompositeVideoClip(video_layers).with_audio(final_audio)
    video.write_videofile(output_video, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")
    
    try:
        video.close(); voice_clip.close(); final_audio.close()
    except: pass
    
    return output_video

# ==========================================
# 6. UPLOAD KE FACEBOOK REELS
# ==========================================
def upload_to_facebook(video_path, caption, index):
    print(f"[{index}/5] 🚀 Mengunggah Firman Tuhan ke Facebook Reels...")
    page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_ACCESS_TOKEN")
    
    init_res = requests.post(f"https://graph.facebook.com/v18.0/{page_id}/video_reels", 
                             data={"upload_phase": "start", "access_token": access_token}).json()
    
    if "video_id" not in init_res:
        raise Exception(f"Ditolak oleh Facebook API! Balasan Meta: {init_res}")
        
    video_fbid, upload_url = init_res["video_id"], init_res["upload_url"]
    
    with open(video_path, 'rb') as f: video_data = f.read()
    requests.post(upload_url, headers={'Authorization': f'OAuth {access_token}', 'offset': '0', 
                                       'file_size': str(os.path.getsize(video_path))}, data=video_data)
    
    print("   -> Menunggu server Meta memproses video (15 detik)...")
    time.sleep(15)
    
    pub_res = requests.post(f"https://graph.facebook.com/v18.0/{page_id}/video_reels", data={
        "access_token": access_token, "video_id": video_fbid, "upload_phase": "finish",
        "video_state": "PUBLISHED", "description": caption
    }).json()
    
    if pub_res.get("success"): 
        print(f"[{index}/5] 🎉 BERHASIL DIUNGGAH KE FACEBOOK REELS!\n")
    else: 
        raise Exception(f"Gagal Publikasi: {pub_res}")

# ==========================================
# EKSEKUTOR UTAMA
# ==========================================
if __name__ == "__main__":
    JUMLAH_VIDEO = 5 
    print(f"✝️ MEMULAI BOT PENGINJIL DIGITAL ({JUMLAH_VIDEO} VIDEO) ✝️\n")
    
    batch = generate_bible_content(JUMLAH_VIDEO)
    
    for i, item in enumerate(batch, 1):
        try:
            print(f"--- MENGERJAKAN VIDEO {i} DARI {len(batch)} ---")
            naskah_suara = f"{item['ayat']} {item['renungan'].replace(chr(10), ' ')} {item['cta']}"
            
            img_bg = os.path.join(BASE_DIR, f"jesus_bg_{i}.jpg")
            audio_file = os.path.join(BASE_DIR, f"voice_{i}.mp3")
            output_file = os.path.join(BASE_DIR, f"bible_reels_{i}.mp4")
            
            caption = f"{item['ayat']}\n\n{item['renungan']}\n\n{item['cta']}\n\n#FirmanTuhan #AyatAlkitab #RenunganHarian #TuhanYesus #Kristen #Rohani #InspirasiKristen"
            
            generate_cinematic_jesus(item['prompt_gambar'], img_bg)
            generate_edge_tts_voice(naskah_suara, audio_file)
            render_bible_video(img_bg, audio_file, item, output_file)
            
            if os.path.exists(output_file):
                upload_to_facebook(output_file, caption, i)
            else:
                raise Exception("File video hilang sebelum di-upload!")
            
            if i < len(batch):
                waktu_jeda = random.randint(60, 180)
                print(f"⏳ Keamanan Anti-Spam aktif: Beristirahat selama {waktu_jeda} detik...\n")
                time.sleep(waktu_jeda)
                
        except Exception as e:
            print(f"❌ Kesalahan pada video {i}: {e}\n")
            
    print("🎉 SEMUA TUGAS SELESAI! 5 VIDEO FIRMAN TUHAN TELAH BERHASIL DIBUAT DAN DIUNGGAH! 🎉")
