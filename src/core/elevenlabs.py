"""
ElevenLabs audio generation - Implemented as a simple function.
Ref: https://elevenlabs.io/docs/api-reference/text-to-dialogue
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from elevenlabs import save
from elevenlabs.client import ElevenLabs

load_dotenv()

def generate_audio_from_script(dialogue: list[dict], output_file: str, voice_id_skeptic: str, voice_id_analyst: str) -> str:
    # 1. Validate API Key
    api_key = os.getenv("ELEVEN_LABS_API_KEY2")
    if not api_key:
        raise ValueError("[ERROR] ELEVEN_LABS_API_KEY2 not found in environment variables.")

    # 2. Initialize Client
    try:
        elevenlabs = ElevenLabs(api_key=api_key)
        
        # 3. Batching Logic
        # La API de Text to Dialogue maneja listas, pero para evitar timeouts o limites
        # excesivos en diálogos muy largos, mantenemos un batching conservador (aprox 5k caracteres).
        MAX_CHARS = 5000 
        batches = []
        current_batch = []
        current_chars = 0
        
        for line in dialogue:
            # NOTA: Ya no extraemos 'emotion_tag' porque el nuevo JSON incluye
            # los tags de audio (ej: [smug], <break>) directamente en el texto.
            text = line.get("text", line.get("line", ""))
            character = line.get("character", "")
            
            # Asignar Voice ID según el personaje
            if character == "Skeptic":
                voice_id = voice_id_skeptic
            else:
                voice_id = voice_id_analyst # Default to Analyst if unknown

            # Preparar objeto input según documentación oficial
            input_item = {
                "text": text,
                "voice_id": voice_id
            }

            line_len = len(text)
            
            # Verificar limite de caracteres para cerrar el batch actual
            if current_chars + line_len > MAX_CHARS and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_chars = 0
            
            current_batch.append(input_item)
            current_chars += line_len
            
        if current_batch:
            batches.append(current_batch)

        print(f"[AUDIO] Generating audio in {len(batches)} batches...")
        
        # 4. Generator function to stream audio
        def audio_generator():
            for i, batch in enumerate(batches):
                print(f"[AUDIO] Processing batch {i+1}/{len(batches)} with model 'eleven_v3'...")
                
                # Llamada a la API: Text to Dialogue
                # Docs: https://elevenlabs.io/docs/api-reference/text-to-dialogue
                audio_stream = elevenlabs.text_to_dialogue.convert(
                    inputs=batch,
                    model_id="eleven_v3", # Recomendado para baja latencia y buen manejo de tags
                    output_format="mp3_44100_128"
                )
                
                # Yield bytes from the stream efficiently
                if hasattr(audio_stream, '__iter__') and not isinstance(audio_stream, (bytes, str)):
                    yield from audio_stream
                else:
                    yield audio_stream

        # 5. Save the audio file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        save(audio_generator(), str(output_path))

        success_msg = f"[SUCCESS] Audio successfully saved to {output_file}"
        print(f"\n{success_msg}")
        return success_msg

    except Exception as e:
        error_msg = f"[ERROR] ElevenLabs API error: {str(e)}"
        print(f"\n{error_msg}")
        raise RuntimeError(error_msg)