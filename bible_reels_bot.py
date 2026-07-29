import os
import time
import random
import requests
import urllib.parse
import google.generativeai as genai
from moviepy import AudioFileClip, CompositeAudioClip, CompositeVideoClip, ColorClip, ImageClip, concatenate_audioclips
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.abspath(os.getcwd())

# ==========================================
# KONFIGURASI API (GEMINI & ELEVENLABS)
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
# ID Suara ElevenLabs (Masukkan ID 'Marcus' atau gunakan 'pNInz6obpgDQGcFmaJgB' untuk 'Adam' yang sangat berwibawa)
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB") 

genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# 1. GEMINI AI: GENERATOR AYAT & RENUNGAN
# ==========================================
def generate_bible_content(num_videos=5):
    print(f"🕊️ Memohon hikmat Gemini AI untuk meracik {num_videos} renungan Firman Tuhan...")
    
    prompt = f"""
    Bertindaklah sebagai Pendeta dan konten kreator rohani Kristen yang penuh karisma. 
    Buatlah {num_videos} naskah video pendek (Reels) berdasarkan ayat Alkitab.
    Gunakan pemisah '---' antar naskah. Format persis seperti ini:
    
    AYAT: [Kutipan ayat Alkitab, misal: "Tuhan adalah gembalaku, takkan kekurangan aku." - Mazmur 23:1]
    RENUNGAN: [Renungan singkat yang sangat mendalam, menyentuh hati, dan menguatkan iman. Panjang 2-3 kalimat]
    CTA: [Ajakan interaksi, misal: Ketik "Amin" jika kamu percaya janji Tuhan!]
    PROMPT_GAMBAR: [Deskripsi bahasa Inggris untuk AI Gambar. Harus berisi: Cinematic portrait of Jesus Christ, highly detailed, photorealistic, cinematic lighting, 8k, divine atmosphere, holy light, [tambahkan detail latar sesuai ayat]]
    """
    
    model = genai.GenerativeModel('gemini-3.5-flash')
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            raw_text = response.text
            break 
        except Exception as e:
            print(f"⚠️ Limit API, bot berdoa (menunggu) 65 detik... (Percobaan {attempt+1})")
            time.sleep(65)
    else:
        raise Exception("❌ Gagal terhubung ke Gemini AI.")

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
    # Menambahkan instruksi ketat agar gambar vertikal dan sinematik
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
# 3. ELEVENLABS API: SUARA BERWIBAWA (MARCUS)
# ==========================================
def generate_elevenlabs_voice(text, output_audio):
    print("🎙️ Merekam suara berwibawa menggunakan ElevenLabs...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.45,       # Lebih beremosi
            "similarity_boost": 0.85 # Mengikuti karakter asli suara (wibawa)
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(output_audio, 'wb') as f:
            f.write(response.content)
        return output_audio
    else:
        raise Exception(f"Error ElevenLabs: {response.text}")

# ==========================================
# 4. TEKS ESTETIK BIBLE REELS
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

def create_text_overlay(item, output_path, img_size=(1080, 1920)):
    img = Image.new("RGBA", img_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_path = get_custom_font()
    font_ayat = ImageFont.truetype(font_path, 50)
    font_renungan = ImageFont.truetype(font_path, 42)
    font_cta = ImageFont.truetype(font_path, 45)
    
    max_w = img_size[0] - 140 
    
    def wrap_text(text, font):
        words = text.split()
        lines, curr = [], ""
        for w in words:
            test = f"{curr} {w}".strip()
            if (draw.textbbox((0,0), test, font=font)[2]) <= max_w: curr = test
            else: lines.append(curr); curr = w
        if curr: lines.append(curr)
        return lines

    blocks = [
        (wrap_text(item['ayat'], font_ayat), font_ayat, "gold", 350),
        (wrap_text(item['renungan'], font_renungan), font_renungan, "white", 800),
        ([f"🙏 {item['cta']}"], font_cta, "cyan", 1450)
    ]
    
    for lines, font, color, y in blocks:
        for line in lines:
            w = draw.textbbox((0,0), line, font=font)[2]
            x = (img_size[0] - w) // 2
            # Efek Outline Hitam Tebal
            for ax, ay in [(-3,0),(3,0),(0,-3),(0,3),(-3,-3),(3,3)]:
                draw.text((x+ax, y+ay), line, font=font, fill="black")
            draw.text((x, y), line, font=font, fill=color)
            y += 70
    img.save(output_path)
    return output_path

# ==========================================
# 5. EDITOR VIDEO (MIX AUDIO + BGM + GAMBAR)
# ==========================================
def render_bible_video(img_bg_path, voice_path, item, output_video):
    print("🎬 Merakit Video Firman Tuhan (Mixing Audio & Visual)...")
    
    # 1. Siapkan Voiceover
    voice_clip = AudioFileClip(voice_path)
    video_duration = voice_clip.duration + 2.0 
    
    # 2. Siapkan Background Music (BGM Soft Piano)
    bgm_file = os.path.join(BASE_DIR, "bgm.mp3")
    final_audio = voice_clip # Default jika BGM tidak ada
    
    if os.path.exists(bgm_file):
        print("   -> Menambahkan musik latar surgawi (BGM)...")
        bgm_clip = AudioFileClip(bgm_file)
        
        # Mengecilkan volume BGM (10% dari asli) agar suara Marcus tetap dominan
        try:
            bgm_clip = bgm_clip.volumex(0.12)
        except AttributeError:
            bgm_clip = bgm_clip.multiply_volume(0.12) # Fallback moviepy v2
            
        # Looping BGM jika lebih pendek dari narasi
        if bgm_clip.duration < video_duration:
            n_loops = int(video_duration // bgm_clip.duration) + 1
            bgm_clip = concatenate_audioclips([bgm_clip] * n_loops)
            
        bgm_clip = bgm_clip.subclipped(0, video_duration)
        
        # Menggabungkan BGM + Voice (Voice mulai setelah 0.5 detik)
        final_audio = CompositeAudioClip([bgm_clip, voice_clip.with_start(0.5)])
    
    # 3. Siapkan Visual (Background Gambar AI)
    visual_clip = ImageClip(img_bg_path).with_duration(video_duration)
    
    # 4. Siapkan Overlay Gelap & Teks
    overlay = ColorClip(size=(1080, 1920), color=(0,0,0)).with_opacity(0.55).with_duration(video_duration)
    txt_img_path = create_text_overlay(item, os.path.join(BASE_DIR, "bible_text_temp.png"))
    txt_clip = ImageClip(txt_img_path).with_duration(video_duration)
    
    # 5. Render Final
    video = CompositeVideoClip([visual_clip, overlay, txt_clip]).with_audio(final_audio)
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
    
    if pub_res.get("success"): print(f"[{index}/5] 🎉 BERHASIL DIUNGGAH!\n")
    else: raise Exception(f"Gagal Upload: {pub_res}")

# ==========================================
# EKSEKUTOR UTAMA
# ==========================================
if __name__ == "__main__":
    print("✝️ MEMULAI BOT PENGINJIL DIGITAL (5 VIDEO) ✝️\n")
    
    batch = generate_bible_content(5)
    
    for i, item in enumerate(batch, 1):
        try:
            print(f"--- MENGERJAKAN VIDEO {i} DARI 5 ---")
            naskah_suara = f"{item['ayat']} {item['renungan'].replace(chr(10), ' ')} {item['cta']}"
            
            img_bg = os.path.join(BASE_DIR, f"jesus_bg_{i}.jpg")
            audio_file = os.path.join(BASE_DIR, f"voice_{i}.mp3")
            output_file = os.path.join(BASE_DIR, f"bible_reels_{i}.mp4")
            
            caption = f"{item['ayat']}\n\n{item['renungan']}\n\n{item['cta']}\n\n#FirmanTuhan #AyatAlkitab #RenunganHarian #TuhanYesus #Kristen #Rohani #InspirasiKristen"
            
            # Eksekusi Tahapan
            generate_cinematic_jesus(item['prompt_gambar'], img_bg)
            generate_elevenlabs_voice(naskah_suara, audio_file)
            render_bible_video(img_bg, audio_file, item, output_file)
            
            upload_to_facebook(output_file, caption, i)
            
            if i < 5:
                print("⏳ Jeda 60 detik anti-spam Facebook...\n")
                time.sleep(60)
                
        except Exception as e:
            print(f"❌ Kesalahan pada video {i}: {e}\n")
