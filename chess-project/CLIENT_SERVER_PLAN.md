# Kung Fu Chess — אפיון Client/Server

> מסמך זה הוא **אפיון בלבד** — שום דבר ממנו לא יְמומש עד שתשלחי מספר/שם איטרציה ספציפי מתוך הרשימה בסעיף 4. כל איטרציה תמומש בשלב נפרד, בצעדים קטנים, עם בקשת אישור לפני כל שינוי משמעותי (ובפרט לפני העברה/מחיקה של קבצים קיימים) — בהתאם לאופן העבודה שסוכם.

---

## 1. מהלך התכנון בקצרה

הפרויקט עובר מ"משחק מקומי אחד מול לוח" לארכיטקטורת **Client–Server**: השרת (בשלב הראשון — מקומי) מנהל משתמשים, דירוג, חדרים והתאמות, ומריץ את מנוע המשחק בפועל; הלקוח אחראי רק לקלט/פלט (קליקים, ציור) ולתקשורת עם השרת. השניים מדברים דרך **WebSocket**, והתקשורת הפנימית בצד השרת בין הרכיבים (Matchmaking, Rooms, Auth, Game Session) מתבצעת דרך **Event Bus** (Pub/Sub), כדי שהרכיבים לא יהיו תלויים ישירות זה בזה. חוקי המשחק, מודל הלוח וההתקדמות בזמן (`model` / `rules` / `realtime` הקיימים) עוברים ל־**`shared/`** כי הם נחוצים גם ללקוח (בדיקת חוקיות מקומית לפני שליחה לשרת) וגם לשרת (המקור היחיד לאמת). האפיון בנוי כסדרת איטרציות קטנות: תשתית תקשורת ריקה קודם, אחר כך Bus, אחר כך DB/Auth, אחר כך מסכי הבית/חדרים/matchmaking, ורק בסוף חיבור מנוע המשחק עצמו וה-UI הגרפי הקיים — כך שבכל שלב יש משהו רץ וניתן לבדיקה, והסיכון לקוד הקיים (`game-chess`) מרוכז בצעד ה-reorganization הראשון בלבד.

---

## 2. עקרונות ארכיטקטורה (תמצית)

- **הפרדה מלאה בין UI ללוגיקת משחק** — הלקוח לא מחליט מה חוקי; הוא רק בודק (מול `shared/rules`) לפני שליחה, וה־**שרת הוא הפוסק הסופי**.
- **Client / Server נפרדים לגמרי**, כל אחד בפרויקט/תיקייה משלו, מתקשרים רק דרך רשת (WebSocket), לא דרך imports ישירים אחד מהשני.
- **Shared** — הקוד היחיד שמותר גם ל-client וגם ל-server לייבא ישירות ממנו (לוח, מהלכים, חוקים).
- **Event Bus (Pub/Sub) בצד השרת** — Publishers מפרסמים אירוע ל-Bus; Subscribers/Listeners נרשמים לאירועים ספציפיים בלבד, בלי תלות ישירה ברכיב שפרסם.
- **FastAPI** בצד השרת — גם ל-WebSocket וגם (אם יידרש בהמשך) ל-endpoints רגילים.
- **SQLite** דרך `sqlite3`/thread ייעודי לכל בקשת DB (כדי לא לחסום את ה-event loop של FastAPI ב-I/O סינכרוני) — ללא GUI, ניהול ידני דרך Shell.
- **לוגים** משני הצדדים (client + server) על כל אירוע תקשורת/מערכת.
- **`engine_adapter` נשאר קבוע תחת `server/`** (לא עובר ל-`shared/`) — הוא זקוק לגישה ל-Bus ולמושגי Room/Session שהם server-only מטבעם; `shared/` נשאר "נקי" ממושגים כאלה כדי שגם לקוח שאין לו קשר לשרת יוכל תיאורטית להשתמש בו רק לבדיקת חוקיות מהלכים.
- **Matchmaking הוא Event-Driven, לא polling** — ראו פירוט מלא באיטרציה 6.
- **מבנה הודעות WebSocket** — envelope אחיד קבוע, ראו פירוט מלא באיטרציה 1.

---

## 3. מבנה תיקיות מוצע

מבנה יעד (לאחר סיום כל האיטרציות). כפי שסוכם — זו **ריאורגניזציה מלאה** של `game-chess/` הקיים, אבל תתבצע בהדרגה: איטרציה 0 מעבירה קבצים בצעדים קטנים ומאושרים, לא הכול בבת אחת.

```
chess-project/
│
├── shared/                        # קוד משותף client+server: לוח, מהלכים, חוקים
│   ├── model/                     # Board, GameState, Piece, Position — מ-game-chess/model
│   ├── rules/                     # piece_rules, piece_registry, rule_engine — מ-game-chess/rules
│   └── realtime/                  # motion, realtime_arbiter — מ-game-chess/realtime
│
├── bus/                           # Event Bus — Pub/Sub, ליבת התקשורת הפנימית בשרת
│   ├── event_bus.py               # מנהל את זרימת ההודעות (register/publish)
│   ├── events.py                  # הגדרת סוגי האירועים הנתמכים (enum/dataclasses)
│   ├── listeners/                 # מאזינים קונקרטיים (למשל: on_player_disconnected)
│   ├── publishers/                # רכיבים שמפרסמים אירועים (room, matchmaking, game_session)
│   └── subscribers/               # רישום subscribers לאירועים ספציפיים
│
├── server/                        # כל הלוגיקה של צד השרת
│   ├── main.py                    # entry point — FastAPI app, הרצת השרת
│   ├── network/                   # שכבת התקשורת (FastAPI)
│   │   └── ws_routes.py           # WebSocket endpoint — קליטת/שליחת הודעות ללקוחות
│   ├── auth/                      # Login/Register, ניהול session
│   ├── db/                        # גישה ל-SQLite (thread ייעודי לכל בקשה)
│   │   ├── schema.sql             # טבלת users: username, password, rating
│   │   └── users_repo.py
│   ├── logic/                     # ניהול משחקים/חדרים/matchmaking/ELO
│   │   ├── room_manager.py
│   │   ├── matchmaking.py
│   │   ├── rating.py              # חישוב ELO
│   │   └── game_session.py        # עוטף מנוע משחק (shared) עבור משחק פעיל אחד
│   └── engine_adapter/            # שכבה דקה שמפעילה את game-chess/engine מול shared/ — נשאר קבוע תחת server/ (סעיף 2 להלן)
│
├── client/                        # כל הלוגיקה של צד הלקוח
│   ├── main.py                    # entry point — Command Line: login → מסך בית
│   ├── network/                   # WebSocket client — שליחה/קבלה מהשרת
│   ├── cli/                       # מסכי Command Line: Login, Play, Room (Create/Join/Cancel)
│   ├── input/                     # board_mapper, controller — מ-game-chess/input
│   ├── ui/                        # (מוצמד בסוף התהליך) renderer, sprite_manager, app-ui, img.py — מ-game-chess/ui
│   └── picture/                   # נכסי גרפיקה — game_snapshot (sprites/config.json) — מ-game-chess/ui/game_snapshot
│
└── game-chess/                    # נשאר כארכיון עד סיום ההעברה בפועל, נמחק רק באיטרציה האחרונה
```

**הערה:** שמות התיקיות הם רעיוניים כפי שציינת, לא נעולים — פרט למיקום `engine_adapter` (סעיף 2), שהוחלט סופית.

---

## 4. איטרציות מימוש

כל איטרציה = יחידת עבודה עצמאית שאפשר לשלוח למימוש בנפרד. סדר האיטרציות נבחר כך שבסופה של כל אחת יש משהו שאפשר להריץ ולבדוק.

### איטרציה 0 — ריאורגניזציה של מבנה התיקיות
- יצירת `shared/`, `bus/`, `server/`, `client/` כתיקיות ריקות/עם שלד בלבד.
- העברת `game-chess/model`, `rules`, `realtime` → `shared/` (imports מתעדכנים בהתאם).
- העברת `game-chess/ui`, `input` → `client/` (`ui/`, `input/`).
- **כל העברה נעשית כצעד נפרד עם אישור**, ואחריה הרצת test suite הקיים (`pytest`) לוודא שכלום לא נשבר.
- שום פיצ'ר חדש לא נוסף בשלב הזה.

### איטרציה 1 — תשתית תקשורת בסיסית (שלד) + מבנה הודעות WebSocket
- `server/main.py` — FastAPI app + WebSocket endpoint ריק (echo בלבד).
- `client/network/` — חיבור WebSocket מהלקוח לשרת.
- `client/main.py` — הרצת CLI מינימלי שמתחבר לשרת, שולח הודעת טקסט, מקבל echo.
- לוגים בשני הצדדים על כל חיבור/הודעה.
- **מבנה הודעות (envelope) קבוע, זהה לשני הכיוונים**, נשלח כ-JSON דרך `websocket.receive_json()`/`send_json()` של FastAPI:
  ```json
  {
    "type": "string",       // סוג ההודעה, למשל "login" / "move" / "game_update" / "error"
    "payload": { ... },     // תוכן ספציפי לסוג
    "request_id": "string", // אופציונלי — לשיוך תגובה לבקשה ספציפית
    "ts": 0                 // אופציונלי — מילישניות, לצורך לוגים
  }
  ```
  - צד השרת מנתב לפי שדה `type` (dispatcher: `type → handler`); כל handler בפועל מפרסם אירוע מתאים ל-`bus/` או קורא ישירות ל-`room_manager`/`engine_adapter`.
  - סוגי הודעות **client→server** (רשימה ראשונית, תורחב בכל איטרציה רלוונטית): `login`, `register`, `play`, `cancel_play`, `create_room`, `join_room`, `cancel_room`, `move`, `jump`, `resign`.
  - סוגי הודעות **server→client**: `login_result`, `match_found`, `match_timeout`, `room_state`, `game_update`, `error`, `disconnect_countdown`, `rating_update`.
  - כל סוג הודעה חדש שנוסף באיטרציה מאוחרת יותר מתועד באותה איטרציה, לא כאן מראש.

### איטרציה 2 — Event Bus
- מימוש `bus/event_bus.py`, `bus/events.py`, שלד ל-`listeners/`, `publishers/`, `subscribers/`.
- אירוע לדוגמה אחד מקצה לקצה (למשל `ClientConnected`) — מתפרסם מ-`network/ws_routes.py`, נקלט ע"י listener שרושם ללוג — כדי לוודא שהמנגנון עובד לפני שבונים עליו לוגיקה אמיתית.

### איטרציה 3 — משתמשים, DB ו-Login
- `server/db/schema.sql` — טבלת `users` (username, password, rating — ברירת מחדל 1200).
- `server/db/users_repo.py` — קריאה/כתיבה, כל בקשה רצה ב-thread ייעודי (לא חוסמת את event loop).
- `server/auth/` — הרשמה/התחברות מול ה-DB.
- `client/cli/` — מסך Login (Command Line) ששולח פרטי משתמש לשרת ומקבל הצלחה/כישלון.

### איטרציה 4 — מסך הבית (שלד תפריט)
- לאחר Login מוצלח — תפריט CLI עם שתי אפשרויות: **Play** / **Room** (עדיין ללא לוגיקה — רק ניווט + שליחת הבחירה לשרת ואישור קבלה).

### איטרציה 5 — Room
- יצירת Room ID ייחודי (`Create`), הצטרפות לפי Room ID (`Join`), `Cancel`.
- הצגת ה-Room ID בראש המסך אצל כל המשתתפים בחדר.
- כלל: שני המשתתפים הראשונים = שחקנים, כל השאר = **Viewer**.
- אירועי Bus מתאימים (`RoomCreated`, `PlayerJoinedRoom`, `ViewerJoinedRoom`).

### איטרציה 6 — Matchmaking (Play) ו-ELO — Event-Driven
- **אין polling/סריקה מחזורית של תור ההמתנה.** ההתאמה מתבצעת אירועית:
  1. שחקן שולח `play` → השרת מוסיף אותו לרשימת ממתינים (`matchmaking.py`) ומפרסם `PlayerQueued` ל-`bus/`.
  2. Listener להתאמות מגיב **מיידית** לאירוע `PlayerQueued`: בודק אם יש כבר ממתין אחר בטווח דירוג ±100 ברשימה. אם כן — מפרסם `MatchFound` (נשלח כ-`match_found` לשני הצדדים) ומסיר את שניהם מהתור. אם לא — השחקן ממתין ברשימה עד שיגיע `PlayerQueued` הבא שמתאים לו, או עד timeout.
  3. ה-timeout של 60 שניות ממומש כ-callback מתוזמן (`asyncio` — למשל `loop.call_later`) שנוצר ברגע ה-enqueue; אם חלף בלי שהשחקן שובץ, מפרסם `MatchTimeout` (`match_timeout` ללקוח) ומסיר אותו מהתור.
  - היתרון: תגובה מיידית עם הצטרפות יריב מתאים, בלי latency של מרווח סריקה, ובלי צריכת CPU על scan תקופתי כשאין ממתינים.
- חישוב ועדכון ELO בסיום משחק (`server/logic/rating.py`).

### איטרציה 7 — חיבור מנוע המשחק בפועל
- `server/engine_adapter` (מיקום סופי, ראו סעיף 2) מפעיל את מנוע המשחק הקיים (`game-chess/engine` + `shared/rules`+`realtime`) בתוך `game_session.py`.
- מהלך: **הלקוח בודק תקינות מול `shared/rules` מקומית**; אם תקין — שולח לשרת; השרת מריץ את הבדיקה שוב (מקור אמת יחיד) ומשדר את התוצאה לשני השחקנים + לכל ה-Viewers בחדר.

### איטרציה 8 — טיפול בניתוקים ומקרי קצה
- ניתוק שחקן באמצע משחק → Auto-Resign אחרי 20 שניות, עם Countdown מוצג על המסך.
- מקרי קצה נוספים: הצטרפות משתמש נוסף לחדר קיים באמצע משחק (כ-Viewer), המתנה ממושכת ללא יריב (איטרציה 6), ניסיון הצטרפות ל-Room ID לא קיים.

### איטרציה 9 — חיבור ה-UI הגרפי הקיים
- העברת `client/ui` (renderer, sprite_manager, app-ui, **`img.py`** — ממשיכים להשתמש רק במחלקת `Img` הקיימת, ללא ספריית גרפיקה חדשה) לעבוד מול `client/network` במקום מול מנוע מקומי בלבד.
- קליקים מהממשק הגרפי → `client/input/controller` → בדיקה מקומית → שליחה לשרת → קבלת שידור-חזרה → ציור בפועל.

### איטרציה 10 (אופציונלי, לסוף) — ליטוש
- איחוד/סקירת לוגים, בדיקות (unit/integration) לרכיבי השרת, עדכון `Handoff.md`/מסמכי UI בהתאם למבנה החדש.

---

## 5. מה עדיין פתוח / יוחלט בזמן המימוש בפועל

שלוש ההחלטות שהיו פתוחות כאן (מיקום `engine_adapter`, מנגנון matchmaking, מבנה הודעות WebSocket) **הוכרעו** — ראו סעיף 2 ואיטרציות 1, 6, 7 בהתאמה. אין כרגע נקודות פתוחות נוספות; אם יתגלה צורך בהחלטה נוספת במהלך מימוש איטרציה ספציפית, היא תוצג לאישור באותה נקודה.

---

*מסמך זה מחליף כל תכנון Client/Server קודם. שום קוד לא נכתב עדיין — ממתינה להנחיה על איזו איטרציה להתחיל.*
