from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from storage import get_state, set_state
from llm.client import ask_llm
from notifications import notify_manager

router = Router()

ESCALATE_PHRASES = {"человек", "оператор", "менеджер", "живой", "позови"}


@router.callback_query(F.data == "soft:enter")
async def cb_soft_enter(cb: CallbackQuery, state: FSMContext):
    st = await get_state(cb.from_user.id)
    st["mode"] = "soft"
    st["return_to"] = None
    await set_state(cb.from_user.id, **st)
    await state.clear()
    await cb.message.edit_text(
        "Привет. Я консультант «Тёплого контура», помогаю разобраться, "
        "какой SIP-дом подойдёт под ваш участок. Спрашивайте — отвечу без утайки."
    )
    await cb.answer()


@router.message(F.text)
async def free_text(msg: Message, state: FSMContext):
    st = await get_state(msg.from_user.id)

    # Если в середине жёсткого сценария пришёл свободный текст — переключаемся в soft
    if st["mode"] == "hard" and st.get("hard_step") and st["hard_step"] not in {"greeting"}:
        if not (st["hard_step"].startswith("book_")):
            st["return_to"] = st["hard_step"]
            st["mode"] = "soft"
            await state.clear()

    if st["mode"] != "soft":
        return

    low = msg.text.lower()
    if any(p in low for p in ESCALATE_PHRASES):
        await msg.answer("Передаю запрос менеджеру, он напишет в течение часа.")
        await notify_manager({"type": "escalation", "reason": "user_request", "text": msg.text})
        return

    history = st.get("soft_history", [])
    history.append({"role": "user", "content": msg.text})
    history = history[-10:]

    result = await ask_llm(history, hard_step=st.get("return_to"))

    history.append({"role": "assistant", "content": result["text"]})
    st["soft_history"] = history
    await set_state(msg.from_user.id, **st)

    await msg.answer(result["text"])

    if result["intent"] == "escalate":
        reason = result["fields"].get("reason", "llm_request") if isinstance(result["fields"], dict) else "llm_request"
        await notify_manager({"type": "escalation", "reason": reason, "text": msg.text})