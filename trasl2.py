import sys
from tkinter import messagebox
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from tqdm import tqdm
import os
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_audioclips, CompositeAudioClip,concatenate_videoclips,AudioClip,VideoClip 
from moviepy.editor import concatenate_videoclips, concatenate_audioclips, AudioFileClip, VideoFileClip,ImageClip
from moviepy.audio.fx.all import audio_loop
from moviepy.video.fx.freeze import freeze
import time
import shutil
from deep_translator import GoogleTranslator
from audio_separator.separator import Separator
from pydub import AudioSegment
import random
from TTS.api import TTS
from moviepy.audio.AudioClip import AudioArrayClip
import numpy as np
import cv2
import subprocess
import speech_recognition as sr 
import ffmpeg
import warnings
import logging

# Sopprimi gli avvisi di UserWarning
warnings.filterwarnings("ignore", category=UserWarning)

# Configura il logger per ignorare i messaggi di WARNING
logging.getLogger("moviepy").setLevel(logging.ERROR)


pathvideo=""
filevideo=""

def downloadVideo_trascription(link):
    global pathvideo,filevideo
    
   
    #download video
    try:
        youtubeObject = YouTube(link)
        youtubeObject = youtubeObject.streams.get_highest_resolution()
        filevideo = youtubeObject.download('.//')
        print("download video success")
    except Exception as erroredownload:
        pathvideo= input("errore Download video, Scarica video Manualmente e Inserisci Il Path> ") 
        filevideo = pathvideo
    #trascrizione
    if "v=" in link:
        video_id = link.split("v=")[1].split("&")[0]
    else:
        print("Invalid link. Please provide a direct link to a YouTube video.")
        return
    # Ottieni la trascrizione per un dato video
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    # Scrivi la trascrizione in un file di testo
    with open('transcript.txt', 'w') as f:
        for line in tqdm(transcript, desc='Writing transcript', unit='line'):
            f.write(str(line) + '\n')
            
def get_video_duration(filename):
    clip = VideoFileClip(filename)
    duration = clip.duration
    clip.close()
    return duration

def separaclipdatrascrizione():
    global filevideo
    filetrasc = ".\\transcript.txt"
    if not pathvideo == "":
        filevideo = pathvideo
    else:
        filevideo = input("Path del video scaricato da entrare le clips> ")

    # Ottieni la durata totale del video
    video_duration = get_video_duration(filevideo)

    # Leggi il file di trascrizione
    with open(filetrasc, 'r') as f:
        transcript = [eval(line) for line in f.readlines()]

    # Ordina la trascrizione per tempo di inizio
    transcript.sort(key=lambda x: x['start'])

    # Inizializza il tempo finale della clip precedente
    prev_end_time = 0

    # Percorri la trascrizione e taglia le clip video
    for i, line in tqdm(enumerate(transcript), total=len(transcript), desc="Estraendo clip", unit="clip"):
        start_time = max(round(line['start'], 3), prev_end_time)
        end_time = min(round(start_time + line['duration'], 3), video_duration)

        # Assicurati che la clip abbia una durata minima
        if end_time - start_time >= 0.5:  # Durata minima di 0.5 secondi
            
            output_file = f".//clips//clip_{i}.mp4"
            
           # Usa ffmpeg-python per l'estrazione della clip con accelerazione GPU
            (
                ffmpeg
                .input(filevideo, ss=start_time, t=end_time-start_time)
                .output(output_file, vcodec='h264_nvenc', acodec='aac', video_bitrate='5M', audio_bitrate='192k')
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )

            print(f"Clip {i:03d} estratta: {start_time} - {end_time}")

            # Aggiorna il tempo finale per la prossima iterazione
            prev_end_time = end_time

        if end_time >= video_duration:
            break

    print("Estrazione delle clip completata.")

def audiotraduzione():
    global filevideo
    if filevideo=="":
        filevideo="traduzioneFilm"
    else:
        os.path.basename(filevideo)
    start_line=0
    
    
    def traduzione(O, l_o, L_t, max_attempts=5, delay=1):
        for attempt in range(max_attempts):
            print(f"battuta originale {O}")
            try:
                result = GoogleTranslator(source=l_o, target=L_t).translate(O.strip())
                return result
            except TypeError:
                print("Errore durante la traduzione, riprovo...")
                time.sleep(delay)  # Aspetta per un po' prima di riprovare
        print("Impossibile tradurre dopo diversi tentativi. Si prega di controllare la connessione o riprovare più tardi.")
        return O

    def separate_audio(output_dir, audio_file,t):
        # Ensure the output directory exists
        output_dir = os.path.abspath(output_dir)  # Convert to absolute path
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # Full path to the input audio file
        input_path = os.path.abspath(audio_file)  # Convert to absolute path
        print(f"Input audio file: {input_path}")
        # Create an instance of Separator
        separator = Separator()
        # Load a machine learning model
        separator.load_model(model_filename='UVR-MDX-NET-Inst_HQ_3.onnx')
        # Try to separate the audio and handle any errors
        try:
            # Separate the audio
            output_files = separator.separate(input_path)
            print(f"Separation complete! Output file(s): {' '.join(output_files)}")
            # Check if the output files were written successfully
            for file in output_files:
                if os.path.exists(file):
                    print(f"File {file} written successfully.")
                else:
                    print(f"File {file} not found.")
        except Exception as e:
            print(f"An error occurred during audio separation: {e}")

    with open("./transcript.txt", 'r') as file:
        lines = file.readlines()
    
    start_line=0
    
    # Per start_line
    while True:
        R=input("Inserisci linea di partenza [0.. maxline trascrizione]> ")
        if R=='':
            break
        start_line = int(R)
        if start_line < len(lines):
            break
        else:
            print(f"Valore non valido. Inserisci un numero tra 0 e {len(lines) - 1}.")
                
    maxripetizioni=0
    maxx=3
    
    #ripeti minimo 3 volte , massimo 10 volte
    while True:
        R2=input("quande volte vuoi riprovare a Syntetizzare la voce se è diverza dalla battuta originale> ")
        
        if R=='':
            break
        maxx= int(R2)
        if (maxx >= 3 and maxx <= 10):
           break
        else:
            print("Valore non valido. Inserisci un numero tra 3 e 10.")
        
       
    
    ling_originale = 'en'
    Ling_traduzione = 'it'
    SL = ""
    print("Elenco lingue: ar, bg, zh, cs, da, nl, en, et, fi, fr, de, el, hu, id, it, ja, ko, lv, lt, no, pl, pt, ro, ru, sk, sl, es, sv, tr, uk")
    lingue = "ar, bg, zh, cs, da, nl, en, et, fi, fr, de, el, hu, id, it, ja, ko, lv, lt, no, pl, pt, ro, ru, sk, sl, es, sv, tr, uk"

    while True:
        SL = input("scegli lingua originale, lingua traduzione> (org,trad)> ")
        if SL == "":
            break
        try:
            a, b = SL.split(',')
            if a in lingue.split(', ') and b in lingue.split(', '):
                ling_originale = a
                Ling_traduzione = b
                break
            else:
                print("Una o entrambe le lingue non sono valide. Riprova.")
        except ValueError:
            print("Formato non valido. Usa 'lingua1,lingua2'.")
    if '.' in filevideo:
        filevideo= os.path.splitext(os.path.basename(filevideo))[0]
    os.makedirs(filevideo,exist_ok=True)
    xtts_v1="tts_models/multilingual/multi-dataset/xtts_v1.1"

    # Inizializza il modello
    tts = TTS(model_name=xtts_v1, progress_bar=True).to("cuda")
    
    for k, line in tqdm(enumerate(lines[start_line:], start=start_line), total=len(lines)-start_line):
            if not os.path.exists(f".\\clips\\clip_{k}.mp4"):
                #esci dal ciclo for
                break
            line = line.strip()
            print(f"Linea originale {k}:  {line}")
            parts = line.split(',')
            text_part = [part for part in parts if 'text' in part]
            if text_part:
                text = text_part[0].split(':')[1].strip().strip("'")
                esclamazione=True
                for parola in text.split():
                    # rileva se cè solo un escalmazione nella battuta come. no, ah, oh , tutte parole che sono uguali dal inglese al italiano, e non ci sono frasi significamente da tradurre 
                    if parola.lower() != 'no' and parola.lower() != 'ah' and parola.lower() != "oh":
                        esclamazione= False
                
                if "[Music]"  in text or "[\xa0__\xa0]"  in text or "[Applause]" in text or esclamazione== True:
                    audio_extract = VideoFileClip(f".\\clips\\clip_{k}.mp4").audio
                    audio_extract.write_audiofile(f".\\{filevideo}\\audio_{k}.wav")
                    #shutil.copyfile(f".\\clips\\clip_{k}.mp4",f".\\{filevideo}\\audio_{k}.mp4")
                else:
                    #traduci clip
                    battuta_originale = text.replace('"', '')
                    battuta_Italiana = traduzione(battuta_originale, ling_originale, Ling_traduzione)
                    # Estrai l'audio dal video
                    clip = VideoFileClip(f".//clips//clip_{k}.mp4")
                    # Ensure the output directory exists
                    output_dir = f".//clips//vocals//clip{k}"
                    output_dir = os.path.abspath(output_dir)  # Convert to absolute path
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    # Crea un percorso temporaneo per il file WAV
                    temp_wav_path = os.path.join(output_dir, f"audio_clip_{k}.wav")
                    temp_wav_path = os.path.abspath(temp_wav_path)  # Convert to absolute path

                    # Scrivi l'audio in formato WAV temporaneo
                    clip.audio.write_audiofile(temp_wav_path)

                    # Converti il WAV in MP3
                    audio = AudioSegment.from_wav(temp_wav_path)
                    mp3_path = os.path.join(output_dir, f"audio_clip_{k}.mp3")
                    mp3_path = os.path.abspath(mp3_path)  # Convert to absolute path
                    audio.export(mp3_path, format="mp3")

                    # Rimuovi il file WAV temporaneo
                    os.remove(temp_wav_path)
                    separate_audio(output_dir, mp3_path, k)
                    if not os.path.exists(f".//clips//vocals//clip{k}//audio_clip_{k}_(Vocals)_UVR-MDX-NET-Inst_HQ_3.wav"):
                        if os.path.exists(f".//audio_clip_{k}_(Vocals)_UVR-MDX-NET-Inst_HQ_3.wav"):
                            shutil.move(f".//audio_clip_{k}_(Vocals)_UVR-MDX-NET-Inst_HQ_3.wav",f".//clips//vocals//clip{k}//")
                    if not  os.path.exists(f".//clips//vocals//clip{k}//audio_clip_{k}_(Instrumental)_UVR-MDX-NET-Inst_HQ_3.wav"):
                        if os.path.exists(f".//audio_clip_{k}_(Instrumental)_UVR-MDX-NET-Inst_HQ_3.wav"):
                            shutil.move(f".//audio_clip_{k}_(Instrumental)_UVR-MDX-NET-Inst_HQ_3.wav",f".//clips//vocals//clip{k}//")
                            
                    print("clona voce Attore/attrice")
                    sintesi_accettabile = False
                    while not sintesi_accettabile:
                        tts.tts_to_file(
                            text=battuta_Italiana,
                            file_path=os.path.join('.//syn_ita', f"clipita{k}.wav"),
                            speaker_wav=f".\\clips\\vocals\\clip{k}\\audio_clip_{k}_(Vocals)_UVR-MDX-NET-Inst_HQ_3.wav",
                            emotion = random.choice(["Happy", "Sad", "Neutral"]),
                            language=Ling_traduzione,
                        )
                        if os.path.exists(os.path.join('.//syn_ita', f"clipita{k}.wav")):
                            recognizer_instance = sr.Recognizer() # Crea una istanza del recognizer
                            wav = sr.AudioFile(os.path.join('.//syn_ita', f"clipita{k}.wav"))
                            try:
                                with wav as source:
                                    recognizer_instance.pause_threshold = 3.0
                                    audio = recognizer_instance.listen(source)
                                    testoriconosciuto = recognizer_instance.recognize_google(audio, language="it-IT")
                                    print(f"battuta ITA: {battuta_Italiana},frase riconosciuta: {testoriconosciuto}")
                                    
                                    parole_riconosciute = 0
                                    parole_totali = 0
                                    
                                    for parola in battuta_Italiana.lower().split():
                                        parole_totali += 1
                                        if parola in testoriconosciuto.lower():
                                            parole_riconosciute += 1
                                    
                                    percentuale_riconosciuta = (parole_riconosciute / parole_totali) * 100
                                    print(f"Percentuale di parole riconosciute: {percentuale_riconosciuta:.2f}%")
                                    
                                    if parole_riconosciute >= (parole_totali // 2):
                                        print("Sintesi accettabile")
                                        sintesi_accettabile = True
                                    else:
                                        print("Sintesi non accettabile, riprovo")
                                    
                            except Exception:
                                sintesi_accettabile = False
                                print("ripeti sintesy")
                                if maxripetizioni < maxx:
                                    maxripetizioni = maxripetizioni + 1
                                else:
                                    print("sintesi accetata")
                                    sintesi_accettabile = True
                        
                    
                    newaudio= []
                    voice_path = os.path.join('.', 'syn_ita', f"clipita{k}.wav")
                    background_path = os.path.join('.', 'clips', 'vocals', f'clip{k}', f'audio_clip_{k}_(Instrumental)_UVR-MDX-NET-Inst_HQ_3.wav')
                    clip_path = os.path.join('.', 'clips', f'clip_{k}.mp4')
                    output_path = os.path.join('.', filevideo, f'audio_{k}.wav')

                    # Assicurati che la directory di output esista
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)

                    duratavoice= AudioFileClip(voice_path).duration
                    duratabackgraund= AudioFileClip(background_path).duration
                    durataclip= VideoFileClip(clip_path).duration
                    
                    clipvideo= VideoFileClip(clip_path)
                    backgraund= AudioFileClip(background_path)
                    voice= AudioFileClip(voice_path)
                    
                    maxdurata=0
                    if duratavoice> durataclip:
                        maxdurata= duratavoice
                        print("DURRATA MAGGIORE VOCE")
                    elif duratavoice< durataclip:
                        maxdurata= durataclip
                        print("DURATA MAGGIORE CLIP VIDEO")
                    elif durataclip== duratavoice:
                        maxdurata= durataclip
                        print("DURATA EQUE")
                    
                    combined_audio = CompositeAudioClip([backgraund.subclip(0,maxdurata),voice.subclip(0,maxdurata)]).set_duration(maxdurata)
                    newaudio.append(combined_audio)
                    # Rimuovi i None se ci sono clip che non sono stati caricati correttamente
                    newaudio = [clip for clip in newaudio if clip is not None]

                    if newaudio:
                        try:
                            final_audio = concatenate_audioclips(newaudio)
                            final_audio.write_audiofile(output_path, 
                                                        codec='pcm_s16le',  # Codec non compresso
                                                        ffmpeg_params=["-ac", "2"],  # Forza 2 canali
                                                        logger=None)  # Disabilita il logging
                        except Exception as e:
                            print(f"Errore durante la scrittura del file audio: {str(e)}")
                    else:
                        print("Nessun audio da concatenare. Il programma termina.")

                    # Chiudi tutti i clip audio
                    for clip in newaudio:
                        clip.close() 
                                                                   
def monta_clip_tradotte():
    global filevideo
    
    if filevideo == "":
        filevideo = "traduzioneFilm"
    def syn_lips():
        durata_audio = 0
        durata_video = 0
        n_clips = len([f for f in os.listdir(".\\clips") if f.endswith((".mp4", ".mkv", ".mov"))])
        ex = ""
        mod = ""
        os.makedirs(".//clips//clips_ITA", exist_ok=True)
        index = 0
        index = int(len([f for f in os.listdir(".//clips//clips_ITA") if f.endswith((".mp4", ".mkv", ".mov"))]) - 1)
        if index < 0:
            index = 0
        cont = ''
        cont = input(f"Riprendi sincronizzazione labbiale dalla clip Ita: {index}")
        m=1
        while True:
            m= input("scegli modello sync lips :: 1 wavlips; 2 wavlips-Gan: ")
            if m=='' or m=='1' or m=='2':
                break
            else:
                print("scelta Errata seleziona 1 wavlips O 2 wavlips-Gan")
        
        
        if cont != '' and cont.isdigit():
            index = int(cont)
        input(f"Ok riprendo dalla clip: {index}")
        for j in tqdm(range(index, n_clips),desc= "Sincronizzazione labbiale"):
            if os.path.exists(f".//clips//clip_{j}.mp4"):
                shutil.copyfile(f".//clips//clip_{j}.mp4", f".//wav2lip//tempclip.mp4")
                ex = ".mp4"
            elif os.path.exists(f".//clips//clip_{j}.mkv"):
                shutil.copyfile(f".//clips//clip_{j}.mkv", f".//wav2lip//tempclip.mkv")
                ex = ".mkv"
            elif os.path.exists(f".//clips//clip_{j}.mov"):
                shutil.copyfile(f".//clips//clip_{j}.mov", f".//wav2lip//tempclip.mov")
                ex = ".mov"
            if os.path.exists(f"{filevideo}//audio_{j}.wav"):
                shutil.copyfile(f"{filevideo}//audio_{j}.wav", f".//wav2lip//tempaudio.wav")
            if (os.path.exists(f".//wav2lip//tempclip{ex}") and os.path.exists(f".//wav2lip//tempaudio.wav")):
                try:
                    os.chdir("wav2lip")
                    if m=='1':
                        os.system(f"python inference.py --checkpoint_path ./checkpoints/wav2lip.pth --face tempclip{ex} --audio tempaudio.wav --resize_factor 2")
                    elif m=='2':
                        os.system(f"python inference.py --checkpoint_path ./checkpoints/wav2lip_gan.pth --face tempclip{ex} --audio tempaudio.wav --resize_factor 2")
                        
                    time.sleep(1)
                    os.chdir('..')
                    mod = "Wav2Lip"
                except ValueError as error:
                    if 'Face not detected! Ensure the video contains a face in all the frames' in str(error):
                        print("Face not detected, executing alternative algorithm.")
                    else:
                        print("Lip sync failed for another reason.")
                except Exception as error:
                    print(f"Lip sync failed for another reason: {str(error)}")
                finally:
                    pass
                time.sleep(1)
                if os.path.exists(".//wav2lip//results//result_voice.mp4"):
                    shutil.move(".//wav2lip//results//result_voice.mp4", f".//clips//clips_ITA//clip_ITA{j}.mp4")
                else:
                    # Execute alternative algorithm without lip synchronization
                    print("Algoritmo alternativo")
                    v = []
                    a = []
                    video_path = f".//clips//clip_{j}{ex}"
                    audio_path= f".//{filevideo}//audio_{j}.wav"
                    if os.path.exists(video_path) and os.path.exists(audio_path):
                        Video = VideoFileClip(video_path)
                        Audio = AudioFileClip(audio_path)
                        v.append(Video)
                        a.append(Audio)
                        durata_video = Video.duration
                        durata_audio = Audio.duration
                        if durata_audio < durata_video:
                            if os.path.exists(f".//clips//vocals//clip{j}audio_clip_{j}_(Instrumental)_UVR-MDX-NET-Inst_HQ_3"):
                                a_ex = concatenate_audioclips([Audio, AudioFileClip(f".//clips//vocals//clip{j}audio_clip_{j}_(Instrumental)_UVR-MDX-NET-Inst_HQ_3")])
                                a_ex = a_ex.subclip(0, durata_video)
                            else:
                                a_ex = concatenate_audioclips([Audio, Audio])
                                a_ex = a_ex.subclip(0, durata_video)
                        elif durata_audio > durata_video:
                            a_ex = Audio.subclip(0, durata_video)
                        else:
                            a_ex = Audio
                        print("sostituisco audio")
                        Video = Video.set_audio(a_ex)
                        Video.write_videofile(f".//clips//clips_ITA//clip_ITA{j}.mp4", codec="libx264", audio_codec="aac")
                        mod = "No Wav2Lip"
                    else:
                        print(f"File video {video_path},audio {audio_path}not found. Skipping this clip.")
                
                    print(f"Video e audio uniti con {mod}")
                    print(f"Durata video: {durata_video}, Durata audio: {durata_audio}")
                    print(f"Percorso video: {video_path}, Percorso audio:.//{filevideo}//audio_{j}.wav")
                    print(f"Audio concatenato: {a_ex}")
                
    syn_lips()
    
    def resize_clips():
        pathfilm = input("Inserisci path (percorso) film: ")    
        if not pathfilm.startswith("./"):
            pathfilm = "./" + pathfilm
        
        if os.path.exists(pathfilm):
            try:
                with VideoFileClip(pathfilm) as video:
                    width, height = video.size
                
                newrisoluzione = input(f"Risoluzione film {width},{height}; vuoi cambiarla? (Inserisci W,H o premi Invio per mantenere): ")
                while newrisoluzione:
                    if ',' in newrisoluzione:
                        try:
                            new_width, new_height = map(int, newrisoluzione.split(','))
                            width, height = new_width, new_height
                            break
                        except ValueError:
                            print(f"Errore: risoluzione non valida: {newrisoluzione}")
                    else:
                        print(f"Errore: formato non valido. Usa 'larghezza,altezza'")
                    newrisoluzione = input("Inserisci nuova risoluzione (W,H) o premi Invio per mantenere: ")
                
                print(f"Risoluzione finale: {width}x{height}")
            
            except Exception as e:
                print(f"Errore nell'apertura del file video: {e}")
                return

            output_dir = "./clips/clips_ITA/finalclips"
            os.makedirs(output_dir, exist_ok=True)
            
            input_dir = "./clips/clips_ITA"
            for clip in tqdm(os.listdir(input_dir), desc="Ridimensionamento clip"):
                if clip.endswith(".mp4"):
                    input_path = os.path.join(input_dir, clip)
                    output_path = os.path.join(output_dir, clip)
                    
                    try:
                        with VideoFileClip(input_path) as clip_video:
                            clip_width, clip_height = clip_video.size
                            if width == clip_width and height == clip_height:
                                shutil.copyfile(input_path, output_path)
                                print(f"Copiato {clip} senza modifiche")
                            else:
                                resized_clip = clip_video.resize(newsize=(width, height))
                                resized_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
                                print(f"Ridimensionato {clip} a {width}x{height}")
                    except Exception as e:
                        print(f"Errore nel processamento di {clip}: {e}")
        else:
            print("Percorso errato")
    resize_clips()
    def montaclips():
        clips_dir = "./clips/clips_ITA/finalclips"
        n_clips = len([clip for clip in os.listdir(clips_dir) if clip.endswith(".mp4")])-1
        output_dir = "./clips/clips_ITA/finalclips/finalFilm"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Numero di clip trovate: {n_clips}")
        input("Premi Invio per iniziare il montaggio...")
        
        if n_clips < 2:
            print("Sono necessarie almeno due clip per il montaggio.")
            return
        
        count = 0
        k = 1
        arrayclips = []
        for j in tqdm(range(n_clips), desc="montaclips"):
            v = VideoFileClip(os.path.join(clips_dir, f"clip_ITA{j}.mp4"))
            print(f"({clips_dir}/clip_ITA{j}.mp4)")
            arrayclips.append(v)
            count += 1
            if count == 80:
                part = concatenate_videoclips(arrayclips)
                partial_output = f"./clips/clips_ITA/finalclips/finalFilm/part{k}.mp4"
                part.write_videofile(partial_output, codec="h264_nvenc", audio_codec="aac", ffmpeg_params=["-preset", "slow", "-crf", "18"])
                k += 1
                count = 0
                arrayclips = []
        
        if arrayclips:
            part = concatenate_videoclips(arrayclips)
            partial_output = f"./clips/clips_ITA/finalclips/finalFilm/part{k}.mp4"
            part.write_videofile(partial_output, codec="h264_nvenc", audio_codec="aac", ffmpeg_params=["-preset", "slow", "-crf", "18"])
        
        n_part = len([part for part in os.listdir(output_dir) if part.startswith("part") and part.endswith(".mp4")])
        arraypart = []
        for j in tqdm(range(n_part), desc="montaclips part"):
            partial_output = f"./clips/clips_ITA/finalclips/finalFilm/part{j+1}.mp4"
            vp = VideoFileClip(partial_output)
            arraypart.append(vp)
        
        complete_output = "./clips/clips_ITA/finalclips/finalFilm/filmtradottocompleto.mp4"
        videofinale = concatenate_videoclips(arraypart)
        videofinale.write_videofile(complete_output, codec="h264_nvenc", audio_codec="aac", ffmpeg_params=["-preset", "slow", "-crf", "18"])         
    montaclips()
                

def pulizia_files_temporanei():
    global filevideo
    
    # Rimuove file con specifici pattern nella directory principale
    for t in os.listdir(".//"):
        if "_(Instrumental)_" in t or "_(Vocals)_" in t:
            os.remove(f".//{t}")
    
    # Directory da cui rimuovere file e cartelle
    directory = ".//clips"
    
    # Itera attraverso gli elementi nella directory
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isfile(item_path):
            os.remove(item_path)  # Rimuove il file
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)  # Rimuove la cartella e tutto il suo contenuto
    
    # Rimuove il file transcript.txt se esiste
    if os.path.exists(".//transcript.txt"):
        os.remove(".//transcript.txt")
    
    # Imposta il valore di filevideo se è vuoto
    if filevideo == "":
        filevideo = ".//traduzioneFilm"
    
    # Rimuove file nella directory syn_ita
    for tfile in tqdm(os.listdir(".//syn_ita"), desc="pulizia files Syn clonazione voce"):
        if os.path.exists(os.path.join('.//syn_ita', tfile)):
            os.remove(os.path.join('.//syn_ita', tfile))
    
    # Rimuove file nella directory clips
    for tfile in tqdm(os.listdir(".//clips"), desc="pulizia files clips"):
        if os.path.exists(os.path.join(".//clips", tfile)):
            try:
                os.remove(os.path.join(".//clips", tfile))
            except Exception as error:
                print(f"ERROR: {error}")
    
    # Controlla se la directory vocals esiste prima di iterare
    vocals_dir = ".//clips//vocals"
    if os.path.exists(vocals_dir):
        # Lista cartelle nella directory vocals
        for k in tqdm(range(len(os.listdir(vocals_dir)) + 1), desc="pulizia files clips vocal"):
            # Se cartella esiste
            dir_path = os.path.join(vocals_dir, f"clip{k}")
            if os.path.exists(dir_path):
                # Leggi file directory
                for tfile in tqdm(os.listdir(dir_path), desc="pulizia files clips vocal dir clip"):
                    # Se il file esiste eliminalo
                    os.remove(os.path.join(dir_path, tfile))
                # Dopo aver eliminato tutti i file, controlla se la directory è vuota
                if not os.listdir(dir_path):
                    # Se la directory è vuota, eliminala
                    os.rmdir(dir_path)
    
    # Rimuove file nella directory filevideo
    for tfile in tqdm(os.listdir(filevideo), desc="pulizia files final"):
        if os.path.exists(os.path.join(filevideo, tfile)):
            os.remove(os.path.join(filevideo, tfile))
    
    print("PULIZIA FILES TEMPORANEI")
        

        
        
        
           

        
    
            
        
   
        
    
                    
                
            
    
def main():
    print("_____________________MENU'________________________________________")
    print("ESEGUI TUTTE LE FUNZIONI : 0")
    print("DOWNLOAD VIDEO & TRASCRIZIONI : 1")
    print("SEPARA CLIPS TRAMITE TRASCRIZIONE : 2")
    print("AUDIO TRADUZIONE : 3")
    print("MONTA TUTTE LE CLIPS INSIEME : 4")
    print("PULISCI FILES TEMPORANEI : 5")

    S= input("SELEZIONA UNA SCELTA DAL MENU> ") 

    if S=='0':
        C='N'
        C= input("SEI SICURO DI VOLER PULIRE TUTTI I DATI CREATI IN PRECECDENZA: 'S' 'N' > ")
        if C=='S' or C=='s':
            pulizia_files_temporanei()
        link = input("inserisci link http: ")
        downloadVideo_trascription(link)
        time.sleep(1)
        separaclipdatrascrizione()
        time.sleep(1)
        audiotraduzione()
        time.sleep(1)
        monta_clip_tradotte()
        time.sleep(1)
    elif S=='1':
        link = input("inserisci link http: ")
        downloadVideo_trascription(link)
    elif S=='2':
        separaclipdatrascrizione()
    elif S=='3':
        audiotraduzione()
    elif S== '4':
        monta_clip_tradotte()
    elif S=='5':
        C='N'
        C= input("SEI SICURO DI VOLER PULIRE TUTTI I DATI CREATI IN PRECECDENZA: 'S' 'N' > ")
        if C=='S' or C=='s':
            pulizia_files_temporanei()

main()