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
    is_admin
)
from fpl_service import FPLService

BOT_TOKEN = os.getenv("BOT_TOKEN", "8934205724:AAFiuwUlxewfvzfRfI3Hw_4RqRtba-z9FNY")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)

def get_main_menu_markup(telegram_id: int = None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_rmt = types.InlineKeyboardButton("🔍 تحليل فريقي (Rate My Team)", callback_data="btn_rmt")
    btn_captain = types.InlineKeyboardButton("👑 ترشيحات الكابتن", callback_data="btn_captain")
    btn_compare = types.InlineKeyboardButton("⚔️ مقارنة لاعبين", callback_data="btn_compare_prompt")
    btn_price = types.InlineKeyboardButton("📈 رادار تغير الأسعار", callback_data="btn_price_watch")
    btn_deadline = types.InlineKeyboardButton("⏳ الديدلاين والوقت المتبقي", callback_data="btn_deadline")
    btn_save = types.InlineKeyboardButton("💾 حفظ رقم فريقي", callback_data="btn_save_team_prompt")
    btn_guide = types.InlineKeyboardButton("ℹ️ كيف تعرف رقم فريقك؟", callback_data="btn_help_id")
    
    markup.add(btn_rmt)
    markup.add(btn_captain, btn_compare)
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
    
    text = (
        "⚽ <b>مرحباً بك في المساعد الذكي لفانتسي الدوري الإنجليزي (FPL Assistant)</b> 🏆\n\n"
        f"📅 <b>{gw_name}:</b>\n{countdown}\n\n"
        f"🛡️ <b>فريقك المسجل:</b>\n{saved_info}\n\n"
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
    
    if state == "waiting_team_id_rmt":
        clear_prompt_state(telegram_id)
        if text_val.isdigit():
            team_id = int(text_val)
            report, entry = FPLService.get_team_analysis(team_id)
            if entry:
                save_user_team(telegram_id, team_id, entry.get("name", ""), entry.get("player_first_name", ""))
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, report, reply_markup=markup)
            return
        else:
            bot.send_message(telegram_id, "⚠️ يرجى إرسال أرقام فقط (رقم الـ ID الخاص بفريقك).")
            return
            
    elif state == "waiting_team_id_save":
        clear_prompt_state(telegram_id)
        if text_val.isdigit():
            team_id = int(text_val)
            report, entry = FPLService.get_team_analysis(team_id)
            if entry:
                save_user_team(telegram_id, team_id, entry.get("name", ""), entry.get("player_first_name", ""))
                msg_text = (
                    f"✅ <b>تم حفظ فريقك بنجاح!</b> 🏆\n\n"
                    f"🛡️ <b>اسم الفريق:</b> {entry.get('name')}\n"
                    f"👤 <b>المدرب:</b> {entry.get('player_first_name')} {entry.get('player_last_name')}\n"
                    f"🔢 <b>الآيدي:</b> <code>{team_id}</code>\n\n"
                    "الآن يمكنك فحص تشكيلتك بنقرة واحدة في أي وقت بدون إعادة إدخال الرقم!"
                )
            else:
                msg_text = "⚠️ لم نتمكن من جلب بيانات الفريق، تأكد من صحة رقم الآيدي."
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔍 فحص تشكيلتي الآن", callback_data="btn_rmt"))
            markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, msg_text, reply_markup=markup)
            return
        else:
            bot.send_message(telegram_id, "⚠️ يرجى إرسال أرقام فقط (رقم الـ ID الخاص بفريقك).")
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
            report, _ = FPLService.get_team_analysis(int(saved["team_id"]))
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 فحص فريق آخر", callback_data="btn_rmt_new"))
            markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, report, reply_markup=markup)
        else:
            set_prompt_state(telegram_id, "waiting_team_id_rmt")
            text = (
                "🔍 <b>تحليل وتقييم التشكيلة (Rate My Team):</b>\n\n"
                "أرسل الآن في الشات <b>رقم الـ ID بتاع فريقك</b> في الفانتسي (أرقام فقط).\n\n"
                "💡 <i>(يمكنك معرفة الرقم بفتح حسابك على موقع الفانتسي ثم الضغط على Points، ستجد الرقم في رابط الصفحة)</i>."
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="btn_main_menu"))
            bot.send_message(telegram_id, text, reply_markup=markup)
        return

    elif data == "btn_rmt_new":
        set_prompt_state(telegram_id, "waiting_team_id_rmt")
        text = "🔍 أرسل الآن في الشات رقم الـ ID بتاع الفريق الذي تريد فحصه:"
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
            types.InlineKeyboardButton("📢 إرسال إعلان إذاعي للكل (Broadcast)", callback_data="btn_admin_broadcast"),
            types.InlineKeyboardButton("🔙 العودة للقائمة", callback_data="btn_main_menu")
        )
        try:
            bot.edit_message_text(text, chat_id=telegram_id, message_id=call.message.message_id, reply_markup=markup)
        except Exception:
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
