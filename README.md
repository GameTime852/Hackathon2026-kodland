# Social Changes

Portal lokalnych inicjatyw społecznych i ekologicznych. Użytkownicy mogą publikować pomysły, komentować je, deklarować udział w akcjach oraz kontaktować się prywatnie z innymi osobami.

## Funkcje

### Dla użytkowników

- rejestracja, logowanie i wylogowanie,
- edycja nicku oraz hasła,
- tworzenie, edycja i usuwanie własnych kart,
- zapisywanie kart jako szkiców i późniejsza publikacja,
- filtrowanie inicjatyw po typie akcji i mieście,
- dołączanie do akcji oraz rezygnacja z udziału,
- komentowanie kart,
- usuwanie własnych komentarzy,
- wyświetlanie listy uczestników własnej inicjatywy,
- czat prywatny z wykorzystaniem kodu użytkownika,
- lista rozmów i liczba nieprzeczytanych wiadomości,
- wyświetlanie czasu wiadomości w lokalnej strefie czasowej,
- usunięcie własnego konta.

### Właściciel karty

Właściciel inicjatywy może dodatkowo:

- edytować i usuwać swoją kartę,
- usuwać komentarze pod swoją kartą,
- usuwać uczestników ze swojej akcji.

Właścicielem jest użytkownik, który utworzył kartę. Uprawnienia są sprawdzane po stronie serwera.

### Administrator

Panel administratora jest dostępny pod adresem `/admin/accounts`. Administrator może:

- przeglądać statystyki portalu,
- wyszukiwać konta po e-mailu lub nicku,
- filtrować użytkowników według roli,
- potwierdzić tożsamość użytkownika za pomocą jego e-maila i kodu bezpieczeństwa,
- zmienić hasło użytkownika,
- nadać lub odebrać rolę administratora,
- zakończyć wszystkie sesje użytkownika,
- usunąć konto użytkownika,
- zarządzać kartami, komentarzami i uczestnikami.

## Technologie

- Python 3,
- Flask,
- Flask-SQLAlchemy,
- SQLAlchemy,
- SQLite,
- HTML, CSS i JavaScript.

## Struktura projektu

```text
.
├── main.py                 # aplikacja Flask, modele, trasy i logika
├── hasher.py               # pomocnicze funkcje obliczania hashy
├── requirements.txt        # zależności Pythona
├── instance/               # lokalna baza SQLite
├── static/
│   ├── css/style.css       # style aplikacji
│   └── img/                # logo, ikony i grafiki
└── templates/              # szablony Jinja2
```

## Uruchomienie w Windows

W terminalu PowerShell przejdź do katalogu projektu i wykonaj:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py main.py
```

Następnie otwórz w przeglądarce:

```text
http://127.0.0.1:5000
```

Przy pierwszym uruchomieniu aplikacja automatycznie:

- utworzy katalog `instance`,
- utworzy bazę `instance/diary.db`,
- doda brakujące kolumny do starszej wersji bazy,
- wygeneruje brakujące kody prywatne i kody bezpieczeństwa.

## Baza danych

Aplikacja korzysta z lokalnej bazy SQLite. Zdefiniowane modele to:

- `User` - konto, dane logowania, role i sesje,
- `Card` - inicjatywa lub szkic,
- `Comment` - komentarz do karty,
- `Participation` - udział użytkownika w akcji,
- `PrivateMessage` - wiadomość prywatna.

Udział użytkownika w tej samej karcie może wystąpić tylko raz. Ponowne kliknięcie przycisku usuwa jego udział.

## Najważniejsze trasy

| Trasa | Opis |
| --- | --- |
| `/` i `/login` | logowanie |
| `/register` | rejestracja |
| `/index` | lista inicjatyw i filtry |
| `/account` | konto użytkownika i szkice |
| `/create` | tworzenie karty |
| `/edit_card/<id>` | edycja karty |
| `/card/<id>` | szczegóły karty |
| `/join_card/<id>` | dołączenie lub rezygnacja z udziału |
| `/comment_card/<id>` | dodanie komentarza |
| `/delete_comment/<id>` | usunięcie komentarza |
| `/remove_participant/<id>` | usunięcie uczestnika przez właściciela/admina |
| `/delete_card/<id>` | usunięcie karty |
| `/private_chat` | interfejs czatu prywatnego |
| `/admin/accounts` | panel administratora |
| `/info` | strona informacyjna |

API czatu obejmuje endpointy pobierania i wysyłania wiadomości, long-polling oraz oznaczania wiadomości jako przeczytanych:

```text
/api/private_chat/messages
/api/private_chat/messages/wait
/api/private_chat/send
/api/private_chat/conversations
/api/private_chat/mark_read
```

## Kody użytkownika

Każde konto otrzymuje:

- prywatny kod składający się z 8 znaków, używany do rozpoczęcia rozmowy,
- pięciocyfrowy kod bezpieczeństwa, używany przez administratora do potwierdzenia tożsamości.

Kodu prywatnego należy udostępniać tylko zaufanym osobom. Kod bezpieczeństwa powinien pozostać poufny.


Przed użyciem produkcyjnym należy przede wszystkim zastosować bezpieczne haszowanie haseł, zmienne środowiskowe dla sekretów, ochronę CSRF, wyłączyć tryb debugowania i dodać właściwe migracje bazy.


