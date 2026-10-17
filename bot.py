import os
import re
import telebot
from telebot import types
from datetime import datetime

from database import (
    init_db,
    save_user_team,
    get_user_team,
    set_prompt_state,
    get_prompt_state,
    clear_prompt_state,
    get_all_user_ids,
    get_stats,
    is_admin,
    set_bot_setting,
    get_bot_setting
)
from fpl_service import FPLService

BOT_TOKEN = os.getenv("BOT_TOKEN", "8934205724:AAFiuwUlxewfvzfRfI3Hw_4RqRtba-z9FNY")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)

def get_main_menu_markup(telegram_id: int = None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_rmt = types.InlineKeyboardButton("🔍 تحليل فريقي (Rate My Team)", callback_data="btn_rmt")
    btn_transfer = types.InlineKeyboardButton("🔄 اقتراح تبديل ذكي (مين تبيع وتشتري)", callback_data="btn_transfers")
    btn_wildcard = types.InlineKeyboardButton("🃏 تشكيلة Wildcard بالذكاء الاصطناعي", callback_data="btn_wildcard")
    btn_captain = types.InlineKeyboardButton("👑 ترشيحات الكابتن", callback_data="btn_captain")
    btn_diff = types.InlineKeyboardButton("💎 رادار الديفرينشال (<10%)", callback_data="btn_diff")
    btn_hit = types.InlineKeyboardButton("🧮 حاسبة سالب 4 (-4)", callback_data="btn_hit_prompt")
    btn_compare = types.InlineKeyboardButton("⚔️ مقارنة لاعبين", callback_data="btn_compare_prompt")
    btn_setpiece = types.InlineKeyboardButton("🎯 مسددو الجزاء والكرات الثابتة", callback_data="btn_setpiece")
    btn_rotation = types.InlineKeyboardButton("🛡️ التدوير الدفاعي الرخيص (£4.5m)", callback_data="btn_rotation")
    btn_league = types.InlineKeyboardButton("🏆 دوري البوت الرسمي (Mini-League)", callback_data="btn_league")
    btn_price = types.InlineKeyboardButton("📈 رادار تغير الأسعار", callback_data="btn_price_watch")
    btn_deadline = types.InlineKeyboardButton("⏳ موعد الديدلاين", callback_data="btn_deadline")
    btn_save = types.InlineKeyboardButton("💾 حفظ رقم فريقي", callback_data="btn_save_team_prompt")
    btn_guide = types.InlineKeyboardButton("ℹ️ كيف تعرف رقم فريقك؟", callback_data="btn_help_id")
    
    markup.add(btn_rmt)
    markup.add(btn_transfer)
    markup.add(btn_wildcard)
    markup.add(btn_captain, btn_diff)
    markup.add(btn_hit, btn_compare)
    markup.add(btn_setpiece, btn_rotation)
    markup.add(btn_league)
    markup.add(btn_price, btn_deadline)
    markup.add(btn_save, btn_guide)
    
    if telegram_id and is_admin(telegram_id):
        markup.add(types.InlineKeyboardButton("👑 لوحة تحكم المشرف والإعلانات", callback_data="btn_admin_fpl"))
        
    return markup

@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    telegram_id = message.chat.id
    clear_prompt_state(telegram_id)
    
    saved = get_user_team(telegram_id)
    saved_info = "لم تقم بحفظ رقم فريقك بعد."
    if saved and saved.get("team_id"):
        t_name = saved.get("team_name") or "فريقي"
        saved_info = f"<b>{t_name}</b> (ID: <code>{saved['team_id']}</code>)"
        
    dl_info = FPLService.get_deadline_countdown()
    gw_name = dl_info.get("gw_name", "الجولة القادمة")
    countdown = dl_info.get("countdown", "")
    
    league_code = get_bot_setting("league_code", "")
    league_note = ""
    if league_code:
        league_note = f"🏆 <b>دوري البوت الرسمي:</b> كود: <code>{league_code}</code> <i>(اضغط زر الدوري بالأسفل للانضمام)</i>\n\n"
    
    text = (
        "⚽ <b>مرحباً بك في المساعد الذكي لفانتسي الدوري الإنجليزي (FPL Assistant)</b> 🏆\n\n"
        f"📅 <b>{gw_name}:</b>\n{countdown}\n\n"
        f"🛡️ <b>فريقك المسجل:</b>\n{saved_info}\n\n"
        f"{league_note}"
        "👇 <b>اختر من الخدمات الذكية أدناه:</b>"
    )
    bot.send_message(telegram_id, text, reply_markup=get_main_menu_markup(telegram_id))

@bot.message_handler(commands=['rmt'])
def handle_rmt_command(message):
    telegram_id = message.chat.id
    parts = message.text.split()
    if len(parts) > 1 and parts[1].strip().isdigit():
        team_id = int(parts[1].strip())
        report, entry = FPLService.get_team_analysis(team_id)
        if entry:
            save_user_team(telegram_id, team_id, entry.get("name", ""), entry.get("player_first_name", ""))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, report, reply_markup=markup)
    else:
        saved = get_user_team(telegram_id)
        if saved and saved.get("team_id"):
            report, _ = FPLService.get_team_analysis(int(saved["team_id"]))
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, report, reply_markup=markup)
        else:
            set_prompt_state(telegram_id, "waiting_team_id_rmt")
            text = (
                "🔍 <b>تحليل وتقييم التشكيلة (Rate My Team):</b>\n\n"
                "أرسل الآن في الشات <b>رقم الـ ID بتاع فريقك</b> في الفانتسي.\n\n"
                "💡 <i>(لو مش عارف رقم فريقك، اضغط على زر 'كيف تعرف رقم فريقك' من القائمة الرئيسية)</i>."
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 إلغاء والعودة", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, text, reply_markup=markup)

@bot.message_handler(commands=['transfer', 'transfers'])
def handle_transfer_command(message):
    telegram_id = message.chat.id
    parts = message.text.split()
    if len(parts) > 1 and parts[1].strip().isdigit():
        team_id = int(parts[1].strip())
        bot.send_message(telegram_id, "⏳ جاري فحص تشكيلة فريقك وتحديد أنسب التبديلات...")
        report, entry = FPLService.get_team_transfers(team_id)
        if entry:
            save_user_team(telegram_id, team_id, entry.get("name", ""), entry.get("player_first_name", ""))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, report, reply_markup=markup)
    else:
        saved = get_user_team(telegram_id)
        if saved and saved.get("team_id"):
            bot.send_message(telegram_id, f"⏳ جاري فحص تشكيلة فريقك المسجل (<b>{saved.get('team_name', 'فريقي')}</b>) وتحديد أنسب التبديلات...")
            report, _ = FPLService.get_team_transfers(int(saved["team_id"]))
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, report, reply_markup=markup)
        else:
            set_prompt_state(telegram_id, "waiting_team_id_transfer")
            text = (
                "🔄 <b>اقتراح تبديل ذكي (مين تبيع ومين تشتري):</b>\n\n"
                "أرسل الآن في الشات <b>رقم الـ ID بتاع فريقك</b> في الفانتسي (أرقام فقط)."
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 إلغاء والعودة", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, text, reply_markup=markup)

@bot.message_handler(commands=['swap', 'replace'])
def handle_swap_command(message):
    telegram_id = message.chat.id
    q = message.text.replace("/swap", "").replace("/replace", "").strip()
    if q:
        bot.send_message(telegram_id, f"⏳ جاري البحث عن أفضل بدلاء للاعب {q}...")
        res = FPLService.find_player_swap(q)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, res, reply_markup=markup)
    else:
        bot.send_message(telegram_id, "⚠️ اكتب اسم اللاعب بعد الأمر، مثلاً: <code>/swap بالمر</code> أو <code>/swap Haaland</code>")

@bot.message_handler(commands=['captain', 'cap'])
def handle_captain_command(message):
    text = FPLService.get_captain_recommendations()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['deadline'])
def handle_deadline_command(message):
    dl = FPLService.get_deadline_countdown()
    text = (
        f"⏳ <b>موعد ديدلاين {dl.get('gw_name')}:</b>\n\n"
        f"⏰ {dl.get('deadline_time')}\n\n"
        f"{dl.get('countdown')}\n\n"
        "💡 <i>تأكد من إنهاء كافة التبديلات وتثبيت الكابتن قبل موعد الديدلاين بساعة على الأقل لتجنب ضغط السيرفرات.</i>"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['price'])
def handle_price_command(message):
    text = FPLService.get_price_change_predictions()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['vs'])
def handle_vs_command(message):
    telegram_id = message.chat.id
    parts = message.text.replace("/vs", "").strip().split()
    if len(parts) >= 2:
        name1 = parts[0]
        name2 = parts[1]
        text = FPLService.compare_players(name1, name2)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
    else:
        text = "⚠️ <b>طريقة المقارنة:</b>\nاكتب: <code>/vs Palmer Saka</code> أو <code>/vs بالمر ساكا</code>"
        bot.send_message(telegram_id, text)

@bot.message_handler(commands=['player'])
def handle_player_command(message):
    telegram_id = message.chat.id
    q = message.text.replace("/player", "").strip()
    if q:
        p = FPLService.search_player(q)
        if p:
            card = FPLService.get_player_card(p)
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, card, reply_markup=markup)
        else:
            bot.send_message(telegram_id, f"⚠️ لم يتم العثور على لاعب باسم: {q}")
    else:
        bot.send_message(telegram_id, "⚠️ اكتب اسم اللاعب بعد الأمر، مثلاً: <code>/player هالاند</code>")

@bot.message_handler(commands=['diff', 'differentials'])
def handle_diff_command(message):
    bot.send_message(message.chat.id, "⏳ جاري استخراج أفضل ترشيحات الديفرينشال...")
    text = FPLService.get_differentials()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['wildcard', 'wc'])
def handle_wildcard_command(message):
    bot.send_message(message.chat.id, "⏳ جاري بناء تشكيلة الـ Wildcard بالذكاء الاصطناعي...")
    text = FPLService.get_wildcard_squad()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['hit'])
def handle_hit_command(message):
    telegram_id = message.chat.id
    parts = message.text.replace("/hit", "").strip().split()
    if len(parts) >= 2:
        res = FPLService.calculate_hit(parts[0], parts[1])
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, res, reply_markup=markup)
    else:
        set_prompt_state(telegram_id, "waiting_hit_players")
        text = (
            "🧮 <b>حاسبة قرار سالب 4 (-4 Hit Calculator):</b>\n\n"
            "اكتب الآن في الشات اسم اللاعب الذي تريد بيعه ثم اللاعب الذي تريد شراءه بينهما مسافة:\n\n"
            "• مثال: <code>ايزاك بيدرو</code>\n"
            "• مثال: <code>Eze Palmer</code>\n"
            "• مثال: <code>وود هالاند</code>"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)

@bot.message_handler(commands=['setpiece', 'setpieces', 'penalties', 'pens'])
def handle_setpiece_command(message):
    telegram_id = message.chat.id
    team_query = message.text.replace("/setpiece", "").replace("/setpieces", "").replace("/penalties", "").replace("/pens", "").strip()
    text = FPLService.get_set_piece_takers(team_query if team_query else None)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
    bot.send_message(telegram_id, text, reply_markup=markup)

@bot.message_handler(commands=['rotation', 'pairs'])
def handle_rotation_command(message):
    telegram_id = message.chat.id
    text = FPLService.get_budget_rotation_pairs()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
    bot.send_message(telegram_id, text, reply_markup=markup)

@bot.message_handler(commands=['league', 'dory'])
def handle_league_command(message):
    telegram_id = message.chat.id
    code = get_bot_setting("league_code", "")
    l_id_str = get_bot_setting("league_id", "")
    l_id = int(l_id_str) if l_id_str and l_id_str.isdigit() else None
    
    text, join_url = FPLService.get_league_info(code, l_id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    if join_url:
        markup.add(
            types.InlineKeyboardButton("🌐 انضم للدوري (موقع الفانتسي الرسمي)", url=join_url),
            types.InlineKeyboardButton("📱 انضم للدوري (تطبيق FFM)", url=f"https://fantasyfootballmanager.app/join/{code}")
        )
    markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
    bot.send_message(telegram_id, text, reply_markup=markup)

@bot.message_handler(commands=['setleague'])
def handle_setleague_command(message):
    telegram_id = message.chat.id
    if not is_admin(telegram_id):
        bot.send_message(telegram_id, "⛔ هذا الأمر مخصص لإدارة البوت فقط.")
        return
        
    parts = message.text.replace("/setleague", "").strip().split()
    if not parts:
        cur_code = get_bot_setting("league_code", "غير محدد بعد")
        cur_id = get_bot_setting("league_id", "غير محدد")
        text = (
            "⚙️ <b>إعدادات دوري البوت:</b>\n\n"
            f"• كود الدوري الحالي: <code>{cur_code}</code>\n"
            f"• آيدي الدوري الحالي: <code>{cur_id}</code>\n\n"
            "لتغيير الكود أو الآيدي، اكتب:\n"
            "<code>/setleague CODE</code>\n"
            "أو مع رقم آيدي الدوري لعرض الترتيب:\n"
            "<code>/setleague CODE LEAGUE_ID</code>"
        )
        bot.send_message(telegram_id, text)
        return
        
    new_code = parts[0]
    set_bot_setting("league_code", new_code)
    if len(parts) > 1 and parts[1].isdigit():
        set_bot_setting("league_id", parts[1])
        bot.send_message(telegram_id, f"✅ تم حفظ كود الدوري: <code>{new_code}</code> ورقم الآيدي: <code>{parts[1]}</code> بنجاح!")
    else:
        bot.send_message(telegram_id, f"✅ تم حفظ كود الدوري: <code>{new_code}</code> بنجاح!")

@bot.message_handler(commands=['admin'])
def handle_admin_command(message):
    telegram_id = message.chat.id
    if not is_admin(telegram_id):
        bot.send_message(telegram_id, "⛔ هذا الأمر مخصص لإدارة البوت فقط.")
        return
    stats = get_stats()
    text = (
        "👑 <b>لوحة تحكم مشرف بوت الفانتسي</b> 🛡️\n\n"
        f"👥 إجمالي المستخدمين المسجلين: <b>{stats['total_users']}</b> مستخدم\n\n"
        "👇 <b>اختر الإجراء الإداري:</b>"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 إرسال إعلان إذاعي للكل (Broadcast)", callback_data="btn_admin_broadcast"),
        types.InlineKeyboardButton("🔙 العودة للقائمة", callback_data="btn_main_menu")
    )
    bot.send_message(telegram_id, text, reply_markup=markup)

@bot.message_handler(func=lambda msg: True)
def handle_text_messages(message):
    telegram_id = message.chat.id
    text_val = message.text.strip()
    state = get_prompt_state(telegram_id)
    
    # PRIORITY 1: If user sent any number, treat it as FPL Team ID!
    if text_val.isdigit():
        team_id = int(text_val)
        if state == "waiting_team_id_transfer":
            clear_prompt_state(telegram_id)
            bot.send_message(telegram_id, "⏳ جاري فحص تشكيلة فريقك وتحديد أنسب التبديلات من سيرفرات البريميرليج...")
            try:
                report, entry = FPLService.get_team_transfers(team_id)
                if entry:
                    save_user_team(telegram_id, team_id, entry.get("name", ""), entry.get("player_first_name", ""))
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔍 فحص التشكيلة كاملة (RMT)", callback_data="btn_rmt"))
                markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
                bot.send_message(telegram_id, report, reply_markup=markup)
            except Exception as e:
                print(f"[TransferError] {e}")
                bot.send_message(telegram_id, "⚠️ حدث خطأ أثناء فحص التبديلات. تأكد من صحة رقم الفريق.")
            return
        else:
            clear_prompt_state(telegram_id)
            bot.send_message(telegram_id, "⏳ جاري سحب بيانات تشكيلتك من سيرفرات البريميرليج وفحصها...")
            try:
                report, entry = FPLService.get_team_analysis(team_id)
                if entry:
                    save_user_team(telegram_id, team_id, entry.get("name", ""), entry.get("player_first_name", ""))
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔄 اقترح عليّ تبديلاً لهذا الفريق", callback_data="btn_transfers"))
                markup.add(types.InlineKeyboardButton("🔄 فحص فريق آخر", callback_data="btn_rmt_new"))
                markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
                bot.send_message(telegram_id, report, reply_markup=markup)
            except Exception as e:
                print(f"[RMTException] {e}")
                bot.send_message(telegram_id, "⚠️ حدث خطأ أثناء فحص الفريق. تأكد من أن رقم الـ ID صحيح (رقم فريقك وليس رقم دوري).")
            return

    # PRIORITY 2: Check for swap requests (e.g. "بديل ايزاك" or "swap Haaland")
    clean_lower = text_val.lower()
    if clean_lower.startswith("بديل ") or clean_lower.startswith("swap "):
        p_name = text_val.replace("بديل ", "").replace("swap ", "").replace("Swap ", "").strip()
        if p_name:
            bot.send_message(telegram_id, f"⏳ جاري البحث عن أفضل بدلاء للاعب {p_name}...")
            res = FPLService.find_player_swap(p_name)
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, res, reply_markup=markup)
            return
            
    elif state == "waiting_compare_names":
        clear_prompt_state(telegram_id)
        names = text_val.split()
        if len(names) >= 2:
            res = FPLService.compare_players(names[0], names[1])
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, res, reply_markup=markup)
            return
        else:
            bot.send_message(telegram_id, "⚠️ يرجى كتابة اسم اللاعبين بينهما مسافة، مثلاً: <code>بالمر ساكا</code>")
            return

    elif state == "waiting_hit_players":
        clear_prompt_state(telegram_id)
        names = text_val.split()
        if len(names) >= 2:
            res = FPLService.calculate_hit(names[0], names[1])
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, res, reply_markup=markup)
            return
        else:
            bot.send_message(telegram_id, "⚠️ يرجى كتابة اسم اللاعبين بينهما مسافة، مثلاً: <code>ايزاك بيدرو</code> أو <code>Eze Palmer</code>")
            return

    elif is_admin(telegram_id) and state == "waiting_broadcast_text":
        clear_prompt_state(telegram_id)
        users = get_all_user_ids()
        sent = 0
        for uid in users:
            try:
                bot.send_message(uid, f"📢 <b>إعلان من إدارة فانتسي:</b>\n\n{text_val}")
                sent += 1
            except Exception:
                pass
        bot.send_message(telegram_id, f"✅ تم إرسال الإعلان بنجاح إلى <b>{sent}</b> مستخدم!")
        return

    elif is_admin(telegram_id) and state == "waiting_admin_league_code":
        clear_prompt_state(telegram_id)
        parts = text_val.split()
        if parts:
            code = parts[0]
            set_bot_setting("league_code", code)
            if len(parts) > 1 and parts[1].isdigit():
                set_bot_setting("league_id", parts[1])
                bot.send_message(telegram_id, f"✅ تم حفظ كود الدوري: <code>{code}</code> والآيدي: <code>{parts[1]}</code> بنجاح!")
            else:
                bot.send_message(telegram_id, f"✅ تم حفظ كود الدوري بنجاح: <code>{code}</code>!")
        else:
            bot.send_message(telegram_id, "⚠️ لم يتم إدخال كود صالح.")
        return

    # Natural language shortcuts
    if clean_lower in ["دوري", "الدوري", "league", "دوري البوت", "كود الدوري"]:
        code = get_bot_setting("league_code", "")
        l_id_str = get_bot_setting("league_id", "")
        l_id = int(l_id_str) if l_id_str and l_id_str.isdigit() else None
        text, join_url = FPLService.get_league_info(code, l_id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        if join_url:
            markup.add(
                types.InlineKeyboardButton("🌐 انضم للدوري (موقع الفانتسي الرسمي)", url=join_url),
                types.InlineKeyboardButton("📱 انضم للدوري (تطبيق FFM)", url=f"https://fantasyfootballmanager.app/join/{code}")
            )
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    if clean_lower in ["ديفرينشال", "الدفرينشال", "differential", "differentials", "diff"]:
        bot.send_message(telegram_id, "⏳ جاري استخراج أفضل ترشيحات الديفرينشال...")
        text = FPLService.get_differentials()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    if clean_lower in ["وايلد كارد", "وايلدكارد", "wildcard", "wc"]:
        bot.send_message(telegram_id, "⏳ جاري بناء تشكيلة الـ Wildcard بالذكاء الاصطناعي...")
        text = FPLService.get_wildcard_squad()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    if clean_lower in ["بلنتيات", "ضربات جزاء", "ضربات الجزاء", "فاولات", "penalties", "setpiece"]:
        text = FPLService.get_set_piece_takers()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    if clean_lower in ["تدوير", "تدوير دفاعي", "تدوير الدفاع", "rotation"]:
        text = FPLService.get_budget_rotation_pairs()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    if clean_lower.startswith("سالب 4 ") or clean_lower.startswith("سالب4 ") or clean_lower.startswith("hit "):
        clean_text = re.sub(r'^(سالب 4|سالب4|hit)\s+', '', text_val, flags=re.IGNORECASE).strip()
        names = clean_text.split()
        if len(names) >= 2:
            res = FPLService.calculate_hit(names[0], names[1])
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, res, reply_markup=markup)
            return

    # Check if user sent a player name directly (e.g. "هالاند" or "Palmer")
    player = FPLService.search_player(text_val)
    if player:
        card = FPLService.get_player_card(player)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, card, reply_markup=markup)
        return
        
    # Default fallback
    bot.send_message(
        telegram_id,
        "⚽ أهلاً بك! استخدم القائمة أدناه أو ابحث عن أي لاعب بكتابة اسمه مباشرة (مثال: <code>هالاند</code> أو <code>Palmer</code>):",
        reply_markup=get_main_menu_markup(telegram_id)
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    telegram_id = call.message.chat.id
    data = call.data
    
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
        
    if data == "btn_main_menu":
        clear_prompt_state(telegram_id)
        saved = get_user_team(telegram_id)
        saved_info = "لم تقم بحفظ رقم فريقك بعد."
        if saved and saved.get("team_id"):
            t_name = saved.get("team_name") or "فريقي"
            saved_info = f"<b>{t_name}</b> (ID: <code>{saved['team_id']}</code>)"
            
        dl_info = FPLService.get_deadline_countdown()
        gw_name = dl_info.get("gw_name", "الجولة القادمة")
        countdown = dl_info.get("countdown", "")
        
        text = (
            "⚽ <b>القائمة الرئيسية لمساعد الفانتسي الذكي</b> 🏆\n\n"
            f"📅 <b>{gw_name}:</b>\n{countdown}\n\n"
            f"🛡️ <b>فريقك المسجل:</b>\n{saved_info}\n\n"
            "👇 <b>اختر من الخدمات الذكية:</b>"
        )
        try:
            bot.edit_message_text(text, chat_id=telegram_id, message_id=call.message.message_id, reply_markup=get_main_menu_markup(telegram_id))
        except Exception:
            bot.send_message(telegram_id, text, reply_markup=get_main_menu_markup(telegram_id))
        return

    elif data == "btn_rmt":
        saved = get_user_team(telegram_id)
        if saved and saved.get("team_id"):
            bot.send_message(telegram_id, f"⏳ جاري فحص تشكيلة فريقك المسجل (<b>{saved.get('team_name', 'فريقي')}</b>)...")
            try:
                report, _ = FPLService.get_team_analysis(int(saved["team_id"]))
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔄 فحص فريق آخر", callback_data="btn_rmt_new"))
                markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
                bot.send_message(telegram_id, report, reply_markup=markup)
            except Exception as e:
                print(f"[RMTCallbackError] {e}")
                bot.send_message(telegram_id, "⚠️ تعذر جلب تشكيلة الفريق المسجل حالياً، أرسل رقم فريقك مرة أخرى لتحديثه.")
        else:
            set_prompt_state(telegram_id, "waiting_team_id_rmt")
            text = (
                "🔍 <b>تحليل وتقييم التشكيلة (Rate My Team):</b>\n\n"
                "أرسل الآن في الشات <b>رقم الـ ID بتاع فريقك</b> في الفانتسي (أرقام فقط).\n\n"
                "💡 <i>(يمكنك معرفة الرقم بفتح حسابك على موقع الفانتسي ثم الضغط على Points، ستجد الرقم في رابط الصفحة)</i>."
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("ℹ️ كيف أجد رقم فريقي؟", callback_data="btn_help_id"))
            markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_rmt_new":
        set_prompt_state(telegram_id, "waiting_team_id_rmt")
        text = "🔍 أرسل الآن في الشات رقم الـ ID بتاع الفريق الذي تريد فحصه (أرقام فقط):"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_transfers":
        saved = get_user_team(telegram_id)
        if saved and saved.get("team_id"):
            bot.send_message(telegram_id, f"⏳ جاري فحص تشكيلة فريقك المسجل (<b>{saved.get('team_name', 'فريقي')}</b>) وتحديد أنسب التبديلات...")
            try:
                report, _ = FPLService.get_team_transfers(int(saved["team_id"]))
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔄 فحص تبديلات فريق آخر", callback_data="btn_transfers_prompt"))
                markup.add(types.InlineKeyboardButton("🔍 فحص التشكيلة كاملة (RMT)", callback_data="btn_rmt"))
                markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
                bot.send_message(telegram_id, report, reply_markup=markup)
            except Exception as e:
                print(f"[TransferCallbackError] {e}")
                bot.send_message(telegram_id, "⚠️ تعذر جلب توصيات التبديلات حالياً، أرسل رقم فريقك مرة أخرى لتحديثه.")
        else:
            set_prompt_state(telegram_id, "waiting_team_id_transfer")
            text = (
                "🔄 <b>اقتراح تبديل ذكي (مين تبيع ومين تشتري):</b>\n\n"
                "أرسل الآن في الشات <b>رقم الـ ID بتاع فريقك</b> في الفانتسي (أرقام فقط).\n\n"
                "💡 <i>(لو مش عارف رقم فريقك، اضغط على زر 'كيف أجد رقم فريقي').</i>"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("ℹ️ كيف أجد رقم فريقي؟", callback_data="btn_help_id"))
            markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_transfers_prompt":
        set_prompt_state(telegram_id, "waiting_team_id_transfer")
        text = "🔄 أرسل الآن في الشات رقم الـ ID بتاع الفريق الذي تريد اقتراح تبديلات له (أرقام فقط):"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_captain":
        text = FPLService.get_captain_recommendations()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_compare_prompt":
        set_prompt_state(telegram_id, "waiting_compare_names")
        text = (
            "⚔️ <b>مقارنة لاعبين رأس برأس (Head-to-Head):</b>\n\n"
            "اكتب الآن في الشات اسم اللاعبين بينهما مسافة، مثلاً:\n"
            "• <code>بالمر ساكا</code>\n"
            "• <code>Palmer Saka</code>\n"
            "• <code>هالاند واتكينز</code>"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 إلغاء والعودة", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_price_watch":
        text = FPLService.get_price_change_predictions()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_deadline":
        dl = FPLService.get_deadline_countdown()
        text = (
            f"⏳ <b>موعد ديدلاين {dl.get('gw_name')}:</b>\n\n"
            f"⏰ {dl.get('deadline_time')}\n\n"
            f"{dl.get('countdown')}\n\n"
            "💡 <i>تأكد من إنهاء كافة التبديلات وتثبيت الكابتن قبل موعد الديدلاين بساعة على الأقل لتجنب ضغط السيرفرات.</i>"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_diff":
        bot.send_message(telegram_id, "⏳ جاري استخراج أفضل ترشيحات الديفرينشال...")
        text = FPLService.get_differentials()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_wildcard":
        bot.send_message(telegram_id, "⏳ جاري بناء تشكيلة الـ Wildcard بالذكاء الاصطناعي...")
        text = FPLService.get_wildcard_squad()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_hit_prompt":
        set_prompt_state(telegram_id, "waiting_hit_players")
        text = (
            "🧮 <b>حاسبة قرار سالب 4 (-4 Hit Calculator):</b>\n\n"
            "اكتب الآن في الشات اسم اللاعب الذي تريد بيعه ثم اللاعب الذي تريد شراءه بينهما مسافة:\n\n"
            "• مثال: <code>ايزاك بيدرو</code>\n"
            "• مثال: <code>Eze Palmer</code>\n"
            "• مثال: <code>وود هالاند</code>"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 إلغاء والعودة", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_setpiece":
        text = FPLService.get_set_piece_takers()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_rotation":
        text = FPLService.get_budget_rotation_pairs()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_league":
        code = get_bot_setting("league_code", "")
        l_id_str = get_bot_setting("league_id", "")
        l_id = int(l_id_str) if l_id_str and l_id_str.isdigit() else None
        
        text, join_url = FPLService.get_league_info(code, l_id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        if join_url:
            markup.add(
                types.InlineKeyboardButton("🌐 انضم للدوري (موقع الفانتسي الرسمي)", url=join_url),
                types.InlineKeyboardButton("📱 انضم للدوري (تطبيق FFM)", url=f"https://fantasyfootballmanager.app/join/{code}")
            )
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_save_team_prompt":
        set_prompt_state(telegram_id, "waiting_team_id_save")
        text = (
            "💾 <b>حفظ رقم فريقك الدائم:</b>\n\n"
            "أرسل الآن في الشات <b>رقم الآيدي (Team ID)</b> الخاص بك وسنقوم بحفظه لتتمكن من فحص تشكيلتك في ثانية واحدة دائماً!"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_help_id":
        text = (
            "ℹ️ <b>كيف تجد رقم فريقك (Team ID) في الفانتسي؟</b>\n\n"
            "1. افتح موقع الفانتسي الرسمي من المتصفح: <code>fantasy.premierleague.com</code>\n"
            "2. ادخل على حسابك واضغط على خانة <b>Points</b>.\n"
            "3. بص على شريط الرابط (URL) فوق في المتصفح، هتلاقيه مكتوب بالشكل ده:\n"
            "   <code>.../entry/123456/event/...</code>\n"
            "4. الرقم اللي مكان <b>123456</b> هو ده رقم فريقك بالظبط! انسخه وأرسله هنا."
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_admin_fpl":
        if not is_admin(telegram_id):
            return
        stats = get_stats()
        text = (
            "👑 <b>لوحة تحكم مشرف بوت الفانتسي</b> 🛡️\n\n"
            f"👥 إجمالي المستخدمين المسجلين: <b>{stats['total_users']}</b> مستخدم\n\n"
            "👇 اختر الإجراء المطلوب:"
        )
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("⚙️ تعديل كود دوري البوت", callback_data="btn_admin_setleague"),
            types.InlineKeyboardButton("📢 إرسال إعلان إذاعي للكل (Broadcast)", callback_data="btn_admin_broadcast"),
            types.InlineKeyboardButton("🔙 العودة للقائمة", callback_data="btn_main_menu")
        )
        try:
            bot.edit_message_text(text, chat_id=telegram_id, message_id=call.message.message_id, reply_markup=markup)
        except Exception:
            bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_admin_setleague":
        if not is_admin(telegram_id):
            return
        set_prompt_state(telegram_id, "waiting_admin_league_code")
        cur_code = get_bot_setting("league_code", "غير محدد بعد")
        text = (
            "⚙️ <b>تعديل كود دوري البوت الرسمي:</b>\n\n"
            f"الكود الحالي: <code>{cur_code}</code>\n\n"
            "أرسل الآن في الشات كود الدوري الجديد:\n"
            "• مثال: <code>abc123xy</code>\n"
            "• أو الكود مع الآيدي: <code>abc123xy 987654</code>"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="btn_admin_fpl"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_admin_broadcast":
        if not is_admin(telegram_id):
            return
        set_prompt_state(telegram_id, "waiting_broadcast_text")
        text = (
            "📢 <b>إرسال رسالة إذاعية (Broadcast) لكل مستخدمي البوت:</b>\n\n"
            "اكتب الآن في الشات نص الإعلان الذي تريد إرساله لجميع المستخدمين دفعة واحدة:"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="btn_admin_fpl"))
        bot.send_message(telegram_id, text, reply_markup=markup)
        return

# Inline Query Handler - Viral Growth Machine!
@bot.inline_handler(lambda query: len(query.query) > 0)
def handle_inline_player_query(inline_query):
    try:
        q = inline_query.query.strip()
        player = FPLService.search_player(q)
        results = []
        if player:
            teams = FPLService.get_teams_dict()
            t_short = teams.get(player.get("team"), {}).get("short_name", "")
            cost = player.get("now_cost", 0) / 10.0
            pts = player.get("total_points", 0)
            form = player.get("form", "0.0")
            
            card_content = FPLService.get_player_card(player)
            
            article = types.InlineQueryResultArticle(
                id=str(player["id"]),
                title=f"{player.get('web_name')} ({t_short}) - £{cost:.1f}m",
                description=f"النقاط: {pts} | الفورمة: {form} | المركز: {player.get('element_type')}",
                input_message_content=types.InputTextMessageContent(
                    message_text=card_content,
                    parse_mode="HTML"
                )
            )
            results.append(article)
            
        bot.answer_inline_query(inline_query.id, results, cache_time=60)
    except Exception as e:
        print(f"[InlineError] {e}")

if __name__ == "__main__":
    init_db()
    print("FPL Bot engine loaded successfully!")
