from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states import HardFlow
from storage import get_state, set_state
from keyboards import main_menu, house_type_kb, area_kb, budget_kb, land_kb
from notifications import notify_manager

router = Router()


@router.message(F.text == "/start")
async def cmd_start(msg: Message, state: FSMContext):
    await set_state(
        msg.from_user.id,
        mode="hard",
        hard_step="greeting",
        hard_vars={},
        soft_history=[],
        return_to=None,
        attempts={},
    )
    await state.clear()
    await msg.answer(
        "Привет. «Тёплый контур» — строим тёплые дачные дома из SIP-панелей под ключ.\n"
        "70 м², скандинавский стиль, от 1 900 000 ₽.\n\n"
        "Выберите тему:",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "hard:video_pdf")
async def cb_video_pdf(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer(
        "Вот ваш лид-магнит:\n"
        "• Видео «SIP за 60 секунд» — https://example.com/sip-60s.mp4\n"
        "• PDF «7 главных вопросов про SIP-дома»"
    )
    await set_state(
        cb.from_user.id,
        mode="soft",
        hard_step="greeting",
        return_to=None,
    )
    await state.clear()
    await cb.message.answer(
        "Подключил вас к подписке на 5 писем о SIP за 30 дней. "
        "Если есть вопросы — спрашивайте."
    )
    await cb.answer()


@router.callback_query(F.data == "hard:calculator")
async def cb_calculator(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer(
        "Откройте калькулятор на сайте: https://teplyy-kontur.ru/calculator\n"
        "После расчёта пришлём SMS с бонус-чек-листом «12 пунктов: как выбрать подрядчика SIP-домов»."
    )
    await set_state(cb.from_user.id, mode="soft", hard_step="greeting", return_to=None)
    await state.clear()
    await cb.answer()


@router.callback_query(F.data == "hard:qualify")
async def cb_qualify(cb: CallbackQuery, state: FSMContext):
    await set_state(
        cb.from_user.id,
        mode="hard",
        hard_step="qualify_type",
        hard_vars={},
        attempts={},
    )
    await state.set_state(HardFlow.qualify_type)
    await cb.message.edit_text("Какой дом рассматриваете?", reply_markup=house_type_kb())
    await cb.answer()


@router.callback_query(F.data.startswith("q:house_type:"))
async def q_house_type(cb: CallbackQuery, state: FSMContext):
    choice = cb.data.split(":")[-1]
    st = await get_state(cb.from_user.id)
    st["hard_vars"]["house_type"] = choice
    st["hard_step"] = "qualify_area"
    await set_state(cb.from_user.id, **st)
    await state.set_state(HardFlow.qualify_area)
    await cb.message.edit_text("Какая площадь интересует?", reply_markup=area_kb())
    await cb.answer()


@router.callback_query(F.data.startswith("q:area:"))
async def q_area(cb: CallbackQuery, state: FSMContext):
    choice = cb.data.split(":")[-1]
    st = await get_state(cb.from_user.id)
    st["hard_vars"]["area"] = choice
    st["hard_step"] = "qualify_budget"
    await set_state(cb.from_user.id, **st)
    await state.set_state(HardFlow.qualify_budget)
    await cb.message.edit_text("Какой бюджет на строительство?", reply_markup=budget_kb())
    await cb.answer()


@router.callback_query(F.data.startswith("q:budget:"))
async def q_budget(cb: CallbackQuery, state: FSMContext):
    choice = cb.data.split(":")[-1]
    st = await get_state(cb.from_user.id)
    st["hard_vars"]["budget"] = choice
    st["hard_step"] = "qualify_land"
    await set_state(cb.from_user.id, **st)
    await state.set_state(HardFlow.qualify_land)
    await cb.message.edit_text("Участок уже есть?", reply_markup=land_kb())
    await cb.answer()


@router.callback_query(F.data.startswith("q:land:"))
async def q_land(cb: CallbackQuery, state: FSMContext):
    choice = cb.data.split(":")[-1]
    st = await get_state(cb.from_user.id)
    st["hard_vars"]["land"] = choice
    v = st["hard_vars"]
    is_hot = v.get("budget") in {"1.5-2.5", ">2.5"} and v.get("house_type") != "изучаю"
    is_warm = v.get("budget") in {"1.5-2.5", ">2.5"}

    if is_hot:
        st["hard_step"] = "book_name"
        await set_state(cb.from_user.id, **st)
        await state.set_state(HardFlow.book_name)
        await cb.message.edit_text(
            "Отлично, у нас есть подходящие проекты. "
            "Менеджер проведёт бесплатную видеоконсультацию — 30 минут, в удобное время.\n\n"
            "Напишите имя:"
        )
    elif is_warm:
        await set_state(cb.from_user.id, mode="soft", hard_step="qualify_land", return_to=None)
        await state.clear()
        await cb.message.edit_text(
            "Передам вас консультанту — он ответит на вопросы по технологии "
            "и подскажет, как подготовить участок."
        )
    else:
        await set_state(cb.from_user.id, mode="soft", hard_step="qualify_land", return_to=None)
        await state.clear()
        await cb.message.edit_text(
            "Если только изучаете — подпишитесь на серию «5 писем о SIP за 30 дней», "
            "пришлём материалы без давления. Записать?"
        )
    await cb.answer()


@router.message(HardFlow.book_name)
async def book_name(msg: Message, state: FSMContext):
    st = await get_state(msg.from_user.id)
    st["hard_vars"]["name"] = msg.text.strip()
    st["hard_step"] = "book_phone"
    await set_state(msg.from_user.id, **st)
    await state.set_state(HardFlow.book_phone)
    await msg.answer("Телефон (с кодом города):")


@router.message(HardFlow.book_phone)
async def book_phone(msg: Message, state: FSMContext):
    st = await get_state(msg.from_user.id)
    st["hard_vars"]["phone"] = msg.text.strip()
    st["hard_step"] = "book_time"
    await set_state(msg.from_user.id, **st)
    await state.set_state(HardFlow.book_time)
    await msg.answer("Удобная дата и время для звонка? Например: «завтра в 14:00».")


@router.message(HardFlow.book_time)
async def book_time(msg: Message, state: FSMContext):
    st = await get_state(msg.from_user.id)
    st["hard_vars"]["meeting_time"] = msg.text.strip()
    await set_state(msg.from_user.id, **st)
    await state.clear()
    v = st["hard_vars"]
    await msg.answer(
        f"Записал. Менеджер свяжется в течение 24 часов.\n"
        f"За сутки и за 2 часа до звонка пришлём напоминание со ссылкой на Google Meet.\n\n"
        f"Имя: {v.get('name')}\n"
        f"Телефон: {v.get('phone')}\n"
        f"Время: {v.get('meeting_time')}"
    )
    await notify_manager(st["hard_vars"])