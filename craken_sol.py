#!/usr/bin/env python3
# entropia_generator.py
import os
import sys
import argparse
import hashlib
import subprocess
import shlex
import shutil
import datetime

def read_wordlist(path):
    with open(path, "r", encoding="utf-8") as f:
        words = [w.strip() for w in f.readlines() if w.strip()]
    return words

def bytes_to_bits(b):
    return bin(int.from_bytes(b, "big"))[2:].zfill(len(b)*8)

def bip39_from_entropy(entropy_bytes, wordlist):
    ENT = len(entropy_bytes) * 8
    if ENT not in (128,160,192,224,256):
        raise ValueError("Entropy must be one of: 128,160,192,224,256")
    hash_bits = bytes_to_bits(hashlib.sha256(entropy_bytes).digest())
    entropy_bits = bytes_to_bits(entropy_bytes)
    checksum_len = ENT // 32
    checksum = hash_bits[:checksum_len]
    bits = entropy_bits + checksum
    groups = [bits[i:i+11] for i in range(0, len(bits), 11)]
    if len(wordlist) != 2048:
        raise ValueError("Wordlist must contain exactly 2048 words.")
    indices = [int(g, 2) for g in groups]
    return [wordlist[i] for i in indices]

def run_node_checker(target_dir):
    """Ejecuta node solana_check.mjs dentro de target_dir"""
    mjs = "solana_check.mjs"
    if not os.path.isdir(target_dir):
        print(f"Directorio {target_dir} no existe. No se puede ejecutar el checker.", file=sys.stderr)
        return
    if not os.path.exists(os.path.join(target_dir, mjs)):
        print(f"No se encontró {mjs} en {target_dir}. No se ejecutará el checker.", file=sys.stderr)
        return
    try:
        print(f"Ejecutando checker: node {mjs} en {target_dir}")
        completed = subprocess.run(["node", mjs], cwd=target_dir)
        if completed.returncode != 0:
            print(f"El checker terminó con código {completed.returncode}", file=sys.stderr)
    except Exception as e:
        print("Error ejecutando el checker:", e, file=sys.stderr)

def prompt_handle_existing(output_path, target_dir):
    """
    Si output_path existe, preguntar S/N.
    Si S -> eliminar.
    Si N -> renombrar a mnemonics_X.txt y moverlo dentro de target_dir.
    """
    if not os.path.exists(output_path):
        return

    while True:
        try:
            resp = input(f"Ya existe '{output_path}'. ¿Desea eliminarlo? (S/N): ").strip().lower()
        except EOFError:
            # En caso de ejecuciones no interactivas, asumimos N
            resp = "n"
        if resp in ("s", "si", "y", "yes"):
            try:
                os.remove(output_path)
                print(f"Archivo {output_path} eliminado.")
            except Exception as e:
                print(f"No se pudo eliminar {output_path}: {e}", file=sys.stderr)
                sys.exit(1)
            return
        elif resp in ("n", "no"):
            # Asegurar target_dir existe
            os.makedirs(target_dir, exist_ok=True)
            # Buscar nombre disponible mnemonics_X.txt dentro target_dir
            i = 1
            while True:
                candidate = f"mnemonics_{i}.txt"
                dest = os.path.join(target_dir, candidate)
                if not os.path.exists(dest):
                    break
                i += 1
            try:
                shutil.move(output_path, dest)
                print(f"{output_path} renombrado y movido a {dest}")
            except Exception as e:
                print(f"No se pudo mover {output_path} a {dest}: {e}", file=sys.stderr)
                sys.exit(1)
            return
        else:
            print("Respuesta no válida. Escribe S (sí) o N (no).")

def write_header_and_line(path, line):
    """Escribe cabecera con fecha (formato [YYYY-MM-DD HH:MM:SS]) y luego la línea (sin tocarla)."""
    now = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(path, "w", encoding="utf-8") as f:
        f.write(now + "\n")
        f.write(line + "\n")

def append_line(path, line):
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def main():
    parser = argparse.ArgumentParser(description="Generador de frases BIP-39")
    parser.add_argument("--wordlist", "-w", required=False, help="Ruta al archivo english.txt (2048 palabras)")
    parser.add_argument("--strength", "-s", type=int, default=128, help="128,160,192,224,256")
    parser.add_argument("--output", "-o", default="mnemonics.txt", help="Archivo de salida (por defecto mnemonics.txt)")
    parser.add_argument("--number", "-n", type=int, help="Cantidad de semillas a generar (si no se usa, bucle infinito)")
    parser.add_argument("--test", "-t", type=str, help="Modo test: pasa palabras entre comillas en una sola línea")
    parser.add_argument("--check", action="store_true", help="Si se usa en modo -w con -n: mover mnemonics.txt y ejecutar checker")
    args = parser.parse_args()

    target_dir = os.path.join(".", "tools", "solana_checker")

    # --- MODO TEST ---
    if args.test:
        # No requerimos wordlist en modo test
        words_line = args.test.strip()
        if not words_line:
            print("ERROR: Debes pasar al menos una palabra con --test.", file=sys.stderr)
            sys.exit(1)
        # Manejar archivo existente (pregunta S/N)
        prompt_handle_existing(args.output, target_dir)

        # Escribir header + linea tal cual (sin separar letras)
        write_header_and_line(args.output, words_line)
        print(f"Mnemonic de test guardada en {args.output}:")
        print(words_line)

        # Mover mnemonics.txt a target_dir y ejecutar checker
        os.makedirs(target_dir, exist_ok=True)
        dest = os.path.join(target_dir, os.path.basename(args.output))
        try:
            shutil.move(args.output, dest)
            print(f"Archivo movido a {dest}")
        except Exception as e:
            print(f"Error moviendo {args.output} a {dest}: {e}", file=sys.stderr)
            sys.exit(1)

        run_node_checker(target_dir)
        sys.exit(0)

    # --- MODO NORMAL ---
    # wordlist obligatorio en modo normal
    if not args.wordlist:
        parser.error("Debes usar --wordlist a menos que uses --test")

    if args.strength not in (128,160,192,224,256):
        print("ERROR: strength inválido. Usa uno de: 128,160,192,224,256", file=sys.stderr)
        sys.exit(1)

    if args.check and not args.number:
        print("ERROR: --check solo es aplicable cuando usas -n (cantidad finita).", file=sys.stderr)
        sys.exit(1)

    # leer wordlist
    try:
        wl = read_wordlist(args.wordlist)
    except Exception as e:
        print("Error leyendo wordlist:", e, file=sys.stderr)
        sys.exit(1)

    # Si existe mnemonics.txt preguntar si eliminar o renombrar (y mover renombrado a target_dir)
    prompt_handle_existing(args.output, target_dir)

    # Crear nuevo mnemonics.txt con header (cabecera), luego iremos añadiendo
    now_header = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    try:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(now_header + "\n")
    except Exception as e:
        print(f"Error creando {args.output}: {e}", file=sys.stderr)
        sys.exit(1)

    # Generar
    count = 0
    try:
        while True:
            if args.number and count >= args.number:
                break
            entropy = os.urandom(args.strength // 8)
            words = bip39_from_entropy(entropy, wl)
            mnemonic = " ".join(words)
            print(mnemonic)
            append_line(args.output, mnemonic)
            count += 1
    except KeyboardInterrupt:
        print("\nInterrumpido por usuario. Se conservaron las frases generadas hasta ahora.")

    # Si se pidió check y se generó (o terminó) entonces mover y ejecutar checker
    if args.check:
        # Asegurar target_dir existe
        os.makedirs(target_dir, exist_ok=True)
        dest = os.path.join(target_dir, os.path.basename(args.output))
        try:
            shutil.move(args.output, dest)
            print(f"Archivo movido a {dest}")
        except Exception as e:
            print(f"Error moviendo {args.output} a {dest}: {e}", file=sys.stderr)
            sys.exit(1)
        run_node_checker(target_dir)

if __name__ == "__main__":
    main()
