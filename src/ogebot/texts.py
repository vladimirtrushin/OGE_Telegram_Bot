"""User-facing text templates (Russian). Centralised for easy editing / i18n."""

from __future__ import annotations

from html import escape

from ogebot.db.models import Attempt, Submission, Task, Variant

BOT_NAME = "ОГЭ-Тренажёр"

WELCOME_NEW = (
    "👋 Привет! Это <b>{name}</b> — бот для отработки первой (тестовой) части ОГЭ.\n\n"
    "Здесь можно тренироваться на вариантах по месяцам и мгновенно получать проверку.\n\n"
    "Давай знакомиться. Как тебя зовут? (Имя и фамилия)"
)

WELCOME_BACK = (
    "С возвращением, <b>{name}</b>! 👋\n\n"
    "Выбирай предмет и вариант — и вперёд, решать первую часть."
)

ASK_GRADE = "Отлично, {name}! В каком ты классе? (например, «9А» или пропусти командой /skip)"

REGISTERED = (
    "Готово, регистрация завершена ✅\n\n"
    "Открываю каталог вариантов. Команда /menu — вернуться сюда в любой момент."
)

HELP = (
    "<b>Что умеет {name}</b>\n\n"
    "• /menu — выбрать предмет и вариант\n"
    "• /profile — твой профиль и последние результаты\n"
    "• /cancel — прервать текущее действие\n"
    "• /help — эта справка\n\n"
    "<b>Как решать</b>\n"
    "1. Выбери предмет → месяц (вариант).\n"
    "2. Нажми «Начать вариант».\n"
    "3. Отправляй ответ текстом на каждое задание.\n"
    "4. В конце получишь результат и разбор.\n\n"
    "Ответы проверяются автоматически: регистр, лишние пробелы и запятая в дробях "
    "не важны."
)

CHOOSE_SUBJECT = "📚 Выбери предмет:"
NO_SUBJECTS = "Пока нет ни одного предмета. Загрузите данные командой seed (см. README)."
CHOOSE_VARIANT = "🗓 Предмет: <b>{subject}</b>\nВыбери вариант (месяц):"
NO_VARIANTS = "Для этого предмета пока нет опубликованных вариантов."

CANCELLED = "Действие отменено. /menu — вернуться в каталог."
NOTHING_TO_CANCEL = "Сейчас нечего отменять. /menu — открыть каталог."

ACTIVE_ATTEMPT_HINT = (
    "У тебя есть незавершённый вариант. Продолжай отвечать на текущее задание "
    "или нажми «🚪 Выйти», чтобы завершить его."
)


def variant_card(variant: Variant, task_count: int) -> str:
    lines = [
        f"<b>{escape(variant.title)}</b>",
        f"🗓 {escape(variant.month)}",
        f"📝 Заданий в первой части: <b>{task_count}</b>",
    ]
    if variant.description:
        lines.append("")
        lines.append(escape(variant.description))
    lines.append("")
    lines.append("Готов начать? Нажми кнопку ниже 👇")
    return "\n".join(lines)


def task_message(task: Task, total: int) -> str:
    header = f"<b>Задание {task.number} из {total}</b>"
    hint = _answer_hint(task)
    body = escape(task.statement)
    parts = [header, "", body, "", hint]
    return "\n".join(parts)


def _answer_hint(task: Task) -> str:
    from ogebot.db.models import AnswerType

    if task.answer_type is AnswerType.NUMBER:
        return "✍️ Отправь ответ <b>числом</b>."
    if task.answer_type is AnswerType.SEQUENCE:
        return "✍️ Отправь ответ <b>последовательностью символов</b> (например, 231)."
    return "✍️ Отправь ответ <b>текстом</b>."


def feedback(*, is_correct: bool, user_answer: str, correct_answer: str, show_correct: bool) -> str:
    if is_correct:
        return f"✅ Верно! Твой ответ: <code>{escape(user_answer)}</code>"
    if show_correct:
        return (
            f"❌ Неверно. Твой ответ: <code>{escape(user_answer)}</code>\n"
            f"Правильный ответ: <code>{escape(correct_answer)}</code>"
        )
    return f"Ответ принят: <code>{escape(user_answer)}</code>"


def explanation(text: str) -> str:
    return f"💡 <b>Разбор:</b>\n{escape(text)}"


def _grade_emoji(percent: int) -> str:
    if percent >= 85:
        return "🥇"
    if percent >= 60:
        return "🥈"
    if percent >= 40:
        return "🥉"
    return "📈"


def results(attempt: Attempt, variant: Variant, submissions: list[Submission]) -> str:
    total = attempt.max_score
    percent = round(100 * attempt.score / total) if total else 0
    grade_emoji = _grade_emoji(percent)

    lines = [
        f"{grade_emoji} <b>Результат</b>",
        f"Вариант: {escape(variant.title)}",
        f"Набрано: <b>{attempt.score} из {total}</b> ({percent}%)",
        "",
        "<b>Разбор по заданиям:</b>",
    ]
    answered_task_ids = set()
    for sub in submissions:
        answered_task_ids.add(sub.task_id)
        mark = "✅" if sub.is_correct else "❌"
        lines.append(
            f"{mark} №{sub.task.number}: <code>{escape(sub.user_answer)}</code>"
            + ("" if sub.is_correct else f" → <code>{escape(sub.task.accepted_answers[0])}</code>")
        )
    skipped = total - len(answered_task_ids)
    if skipped > 0:
        lines.append(f"⚪️ Пропущено заданий: {skipped}")
    lines.append("")
    lines.append("Хочешь ещё? /menu — выбрать новый вариант.")
    return "\n".join(lines)


def profile(user_full_name: str, grade: str | None, attempts: list[Attempt]) -> str:
    lines = [
        "<b>👤 Профиль</b>",
        f"Имя: {escape(user_full_name or '—')}",
        f"Класс: {escape(grade or '—')}",
        "",
        "<b>Последние результаты:</b>",
    ]
    if not attempts:
        lines.append("Пока нет завершённых вариантов. /menu — начать первый!")
    else:
        for att in attempts:
            total = att.max_score or 0
            percent = round(100 * att.score / total) if total else 0
            lines.append(f"• {escape(att.variant.title)} — {att.score}/{total} ({percent}%)")
    return "\n".join(lines)
