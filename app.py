import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from games_data import games


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")


DATA_FILE = "data/user_games.json"




def load_user_games():
    """Загружает пользовательские игры из JSON-файла"""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except Exception as e:
        print(f"[ОШИБКА] Не удалось прочитать {DATA_FILE}: {e}")
        flash("Не удалось загрузить сохранённые игры.", "error")
        return []


def save_user_games(games_list):
    """Сохраняет список пользовательских игр в JSON"""
    try:
        # Создаём папку, если её нет
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(games_list, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"[ОШИБКА] Не удалось сохранить {DATA_FILE}: {e}")
        flash("Не удалось сохранить данные.", "error")
        return False



user_games = load_user_games()


# === Маршруты ===

@app.route("/")
def index():
    """Главная страница"""
    return render_template("index.html")


@app.route("/games")
def games_list():
    """Список всех игр: оригинальные + изменённые/добавленные"""
    # Приоритет: если игра есть в user_games — берём её версию
    custom_ids = {g["id"] for g in user_games}
    # Фильтруем оригинальные: только тех, кого нет в user_games
    filtered_games = [g for g in games if g["id"] not in custom_ids]
    # Объединяем
    all_games = user_games + filtered_games
    return render_template("games.html", games=all_games)


@app.route("/add_game", methods=["GET", "POST"])
def add_game():
    """Добавление новой игры"""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        guide = request.form.get("guide", "").strip()

        if not title or not description or not guide:
            flash("Все поля обязательны для заполнения.", "error")
        else:
            # Генерируем уникальный ID
            existing_ids = {g["id"] for g in games} | {g["id"] for g in user_games}
            new_id = max(existing_ids) + 1 if existing_ids else 1

            new_game = {
                "id": new_id,
                "title": title,
                "description": description,
                "image": "placeholder.jpg",
                "guide": guide
            }
            user_games.append(new_game)
            if save_user_games(user_games):
                flash(f'Игра "{title}" успешно добавлена!', "success")
            return redirect(url_for("add_game"))

    return render_template("add_game.html")


@app.route("/edit_game/<int:game_id>", methods=["GET", "POST"])
def edit_game(game_id):

    original_game = None

    # Ищем в оригинальных играх
    for g in games:
        if g["id"] == game_id:
            original_game = g
            break

    # Ищем в пользовательских
    custom_game = next((g for g in user_games if g["id"] == game_id), None)

    if not original_game and not custom_game:
        flash("Игра не найдена.", "error")
        return redirect(url_for("games_list"))

    # Если это оригинальная игра — копируем в user_games
    if original_game and not custom_game:
        # Создаём редактируемую копию
        editable = {
            "id": original_game["id"],
            "title": original_game["title"],
            "description": original_game["description"],
            "image": original_game["image"],
            "guide": original_game.get("guide", "Гайд будет добавлен позже.")
        }
        user_games.append(editable)
        save_user_games(user_games)
        # Перенаправляем на повторный вызов edit_game (теперь найдётся в user_games)
        return redirect(url_for("edit_game", game_id=game_id))

    # Работаем с пользовательской версией
    game = custom_game if custom_game else next(g for g in user_games if g["id"] == game_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        guide = request.form.get("guide", "").strip()

        if not title or not description or not guide:
            flash("Все поля обязательны.", "error")
        else:
            # Обновляем
            game["title"] = title
            game["description"] = description
            game["guide"] = guide

            # Обновляем в списке
            for i, g in enumerate(user_games):
                if g["id"] == game_id:
                    user_games[i] = game
                    break

            if save_user_games(user_games):
                flash("Изменения успешно сохранены!", "success")
            return redirect(url_for("show_guide", game_id=game_id))

    return render_template("edit_game.html", game=game)


@app.route("/guide/<int:game_id>")
def show_guide(game_id):
    """Просмотр гайда — приоритет у user_games"""
    game = next((g for g in user_games if g["id"] == game_id), None)
    if not game:
        game = next((g for g in games if g["id"] == game_id), None)

    if not game:
        flash("Игра не найдена.", "error")
        return redirect(url_for("games_list"))

    return render_template("guide.html", game=game)