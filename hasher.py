import hashlib
import os

def oblicz_hash_tekstu(tekst, algorytm='sha256'):
    """
    Oblicza hash dla podanego ciągu znaków.
    """
    try:
        # Tworzymy obiekt hashujący dla wybranego algorytmu
        hasher = hashlib.new(algorytm)
        # Aktualizujemy hasher zakodowanym ciągiem znaków (UTF-8)
        hasher.update(tekst.encode('utf-8'))
        # Zwracamy wynik w postaci szesnastkowej (hex)
        return hasher.hexdigest()
    except ValueError:
        return f"Błąd: Nieobsługiwany algorytm '{algorytm}'"

def oblicz_hash_pliku(sciezka_pliku, algorytm='sha256'):
    """
    Oblicza hash dla pliku pod wskazaną ścieżką.
    Czyta plik w fragmentach (chunks), aby nie zużyć całej pamięci RAM przy dużych plikach.
    """
    try:
        hasher = hashlib.new(algorytm)
        # Otwieramy plik w trybie odczytu binarnego ('rb')
        with open(sciezka_pliku, 'rb') as plik:
            # Czytamy plik po kawałku (np. 8KB)
            for chunk in iter(lambda: plik.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        return f"Błąd: Nie znaleziono pliku pod ścieżką: '{sciezka_pliku}'"
    except ValueError:
        return f"Błąd: Nieobsługiwany algorytm '{algorytm}'"
    except Exception as e:
        return f"Wystąpił nieoczekiwany błąd: {e}"

def menu(password):
    wynik = oblicz_hash_tekstu(password)
    return wynik
