import time
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/?future=1"
FPL_ENTRY_URL = "https://fantasy.premierleague.com/api/entry/{team_id}/"
FPL_PICKS_URL = "https://fantasy.premierleague.com/api/entry/{team_id}/event/{gw}/picks/"

# Cache storage
_cache: Dict[str, Any] = {}
_cache_ttl = 300  # 5 minutes

POSITION_MAP = {
    1: {"name": "حارس مرمى", "short": "GKP", "emoji": "🧤"},
    2: {"name": "مدافع", "short": "DEF", "emoji": "🛡️"},
    3: {"name": "خط وسط", "short": "MID", "emoji": "🎯"},
    4: {"name": "مهاجم", "short": "FWD", "emoji": "⚽"}
}

ARABIC_NAME_MAP = {
    "هالاند": "Haaland",
    "هلاند": "Haaland",
    "بالمر": "Palmer",
    "كول بالمر": "Palmer",
    "بيدرو": "João Pedro",
    "جواو بيدرو": "João Pedro",
    "شرقي": "Cherki",
    "تشيركي": "Cherki",
    "روجرز": "Rogers",
    "كالفيري": "Calafiori",
    "كالافيوري": "Calafiori",
    "ساكا": "Saka",
    "ويرتز": "Wirtz",
    "فيرتز": "Wirtz",
    "ايزاك": "Isak",
    "إيزاك": "Isak",
    "تاركوفسكي": "Tarkowski",
    "جفارديول": "Gvardiol",
    "باركولا": "Barcola",
    "فريمبونج": "Frimpong",
    "جاكبو": "Gakpo",
    "فودين": "Foden",
    "جابرييل": "Gabriel",
    "ساليبا": "Saliba",
    "رايا": "Raya",
    "واتكينز": "Watkins",
    "مبيومو": "Mbeumo",
    "سون": "Son",
    "فيرجيل": "Virgil",
    "فان دايك": "Virgil",
    "كييزا": "Chiesa",
    "مارتينيلي": "Martinelli",
    "هافرتز": "Havertz",
    "سولانكي": "Solanke",
    "بوين": "Bowen",
    "جوردون": "Gordon",
    "ديلاب": "Delap",
    "وود": "Wood",
    "سيمينيو": "Semenyo",
    "جاكسون": "Jackson"
}

def _get_with_cache(url: str, ttl: int = _cache_ttl) -> Optional[Dict[str, Any]]:
    now = time.time()
    if url in _cache:
        data, ts = _cache[url]
        if now - ts < ttl:
            return data
            
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            res_data = resp.json()
            _cache[url] = (res_data, now)
            return res_data
        else:
            print(f"[FPL_API_ERROR] {url} returned status {resp.status_code}")
    except Exception as e:
        print(f"[FPL_API_EXCEPTION] {url}: {e}")
    return None

class FPLService:
    @classmethod
    def get_bootstrap(cls) -> Dict[str, Any]:
        data = _get_with_cache(FPL_BOOTSTRAP_URL, ttl=300)
        return data or {}

    @classmethod
    def get_fixtures(cls) -> List[Dict[str, Any]]:
        data = _get_with_cache(FPL_FIXTURES_URL, ttl=900)
        return data if isinstance(data, list) else []

    @classmethod
    def get_teams_dict(cls) -> Dict[int, Dict[str, Any]]:
        boot = cls.get_bootstrap()
        return {t["id"]: t for t in boot.get("teams", [])}

    @classmethod
    def get_players_list(cls) -> List[Dict[str, Any]]:
        boot = cls.get_bootstrap()
        return boot.get("elements", [])

    @classmethod
    def get_current_and_next_gw(cls) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        boot = cls.get_bootstrap()
        events = boot.get("events", [])
        current_gw = None
        next_gw = None
        for ev in events:
            if ev.get("is_current"):
                current_gw = ev
            if ev.get("is_next"):
                next_gw = ev
        return current_gw, next_gw

    @classmethod
    def get_deadline_countdown(cls) -> Dict[str, Any]:
        curr, next_ev = cls.get_current_and_next_gw()
        target = next_ev or curr
        if not target:
            return {"text": "لا تتوفر معلومات عن الجولة القادمة حالياً."}

        dl_str = target.get("deadline_time", "")
        gw_name = target.get("name", "الجولة القادمة")
        
        # Parse ISO 8601
        try:
            dl_dt = datetime.fromisoformat(dl_str.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            diff = dl_dt - now_dt
            
            # Convert to Cairo time (UTC+3)
            cairo_hours = (dl_dt.hour + 3) % 24
            time_formatted = f"{dl_dt.strftime('%Y-%m-%d')} الساعة {cairo_hours:02d}:{dl_dt.minute:02d} بتوقيت مصر"
            
            if diff.total_seconds() <= 0:
                countdown_text = "🚨 انتهى الديدلاين بالفعل للجولة الحالية!"
            else:
                days = diff.days
                hours, rem = divmod(diff.seconds, 3600)
                minutes, _ = divmod(rem, 60)
                
                parts = []
                if days > 0:
                    parts.append(f"{days} يوم")
                if hours > 0:
                    parts.append(f"{hours} ساعة")
                parts.append(f"{minutes} دقيقة")
                countdown_text = "⏳ الوقت المتبقي: " + " و ".join(parts)
                
            return {
                "gw_name": gw_name,
                "deadline_time": time_formatted,
                "countdown": countdown_text,
                "is_urgent": diff.total_seconds() < 86400  # less than 24 hours
            }
        except Exception as e:
            print(f"[CountdownError] {e}")
            return {"gw_name": gw_name, "deadline_time": dl_str, "countdown": ""}

    @classmethod
    def search_player(cls, query: str) -> Optional[Dict[str, Any]]:
        clean_q = query.strip()
        if not clean_q:
            return None
            
        # Check Arabic transliteration mapping
        if clean_q in ARABIC_NAME_MAP:
            clean_q = ARABIC_NAME_MAP[clean_q]
        else:
            for ar, en in ARABIC_NAME_MAP.items():
                if ar in clean_q or clean_q in ar:
                    clean_q = en
                    break
                    
        clean_q = clean_q.lower()
        players = cls.get_players_list()
        
        # 1. Exact match on web_name
        for p in players:
            if p.get("web_name", "").lower() == clean_q:
                return p
                
        # 2. Substring in web_name
        for p in players:
            if clean_q in p.get("web_name", "").lower():
                return p
                
        # 3. Substring in first_name + second_name
        for p in players:
            full = f"{p.get('first_name', '')} {p.get('second_name', '')}".lower()
            if clean_q in full:
                return p
                
        return None

    @classmethod
    def get_player_upcoming_fixtures(cls, player: Dict[str, Any], count: int = 3) -> List[Dict[str, Any]]:
        team_id = player.get("team")
        fixtures = cls.get_fixtures()
        teams = cls.get_teams_dict()
        
        curr, next_ev = cls.get_current_and_next_gw()
        start_gw = next_ev.get("id") if next_ev else (curr.get("id", 1) if curr else 1)
        
        out = []
        for f in fixtures:
            if f.get("event") and f.get("event") >= start_gw:
                if f.get("team_h") == team_id:
                    opp = teams.get(f.get("team_a"), {})
                    out.append({
                        "event": f.get("event"),
                        "opp_short": opp.get("short_name", "OPP"),
                        "is_home": True,
                        "fdr": f.get("team_h_difficulty", 3)
                    })
                elif f.get("team_a") == team_id:
                    opp = teams.get(f.get("team_h"), {})
                    out.append({
                        "event": f.get("event"),
                        "opp_short": opp.get("short_name", "OPP"),
                        "is_home": False,
                        "fdr": f.get("team_a_difficulty", 3)
                    })
            if len(out) >= count:
                break
        return out

    @classmethod
    def format_fdr_emoji(cls, fdr: int) -> str:
        if fdr <= 2:
            return f"🟢 ({fdr})"
        elif fdr == 3:
            return f"⚪ ({fdr})"
        else:
            return f"🔴 ({fdr})"

    @classmethod
    def get_player_card(cls, player: Dict[str, Any]) -> str:
        teams = cls.get_teams_dict()
        team_info = teams.get(player.get("team"), {})
        team_name = team_info.get("name", "Unknown")
        team_short = team_info.get("short_name", "")
        
        pos_id = player.get("element_type", 1)
        pos_info = POSITION_MAP.get(pos_id, {"name": "لاعب", "emoji": "⚽"})
        
        price = player.get("now_cost", 0) / 10.0
        total_pts = player.get("total_points", 0)
        selected = player.get("selected_by_percent", "0")
        form = player.get("form", "0.0")
        goals = player.get("goals_scored", 0)
        assists = player.get("assists", 0)
        clean_sheets = player.get("clean_sheets", 0)
        
        # Status / Injury
        status = player.get("status", "a")
        status_text = "✅ جاهز ومتاح للمشاركة"
        if status == "i":
            status_text = f"🚨 مصاب: {player.get('news', 'إصابة')}"
        elif status == "d":
            status_text = f"⚠️ شكوك: {player.get('news', 'مشكوك في مشاركته')}"
        elif status == "s":
            status_text = f"🟥 موقوف: {player.get('news', 'إيقاف')}"
        elif status == "u":
            status_text = f"⛔ غير متاح: {player.get('news', '')}"
            
        fixtures = cls.get_player_upcoming_fixtures(player, count=3)
        fix_lines = []
        for fix in fixtures:
            ha = "داخل" if fix["is_home"] else "خارج"
            fix_lines.append(f"• GW{fix['event']}: ضد <b>{fix['opp_short']}</b> ({ha}) {cls.format_fdr_emoji(fix['fdr'])}")
        fix_text = "\n".join(fix_lines) if fix_lines else "لا توجد مباريات قادمة محددة."
        
        card = (
            f"{pos_info['emoji']} <b>{player.get('first_name', '')} {player.get('second_name', '')}</b> ({player.get('web_name')})\n"
            f"🏟️ النادي: <b>{team_name} ({team_short})</b> | المركز: <b>{pos_info['name']}</b>\n\n"
            f"💰 السعر: <b>£{price:.1f}m</b>\n"
            f"🏆 إجمالي النقاط: <b>{total_pts} نقطة</b>\n"
            f"🔥 الفورمة الحالية: <b>{form}</b>\n"
            f"👥 نسبة الملكية: <b>{selected}%</b>\n\n"
            f"📊 <b>إحصائيات الموسم:</b>\n"
            f"• الأهداف: <b>{goals}</b> | الأسيستات: <b>{assists}</b>"
        )
        if pos_id in [1, 2]:
            card += f" | الشباك النظيفة: <b>{clean_sheets}</b>"
            
        card += (
            f"\n\n🩺 <b>الحالة البدنية:</b>\n{status_text}\n\n"
            f"🗓️ <b>المباريات الـ 3 القادمة وسهولتها (FDR):</b>\n{fix_text}"
        )
        return card

    @classmethod
    def get_captain_recommendations(cls) -> str:
        players = cls.get_players_list()
        teams = cls.get_teams_dict()
        curr, next_ev = cls.get_current_and_next_gw()
        gw_label = next_ev.get("name") if next_ev else (curr.get("name") if curr else "الجولة")
        
        # Filter available premium attackers & midfielders (status == 'a' and cost >= 7.0 and form > 3.0)
        candidates = []
        for p in players:
            if p.get("status") in ["a", "d"] and p.get("element_type") in [3, 4]:
                try:
                    form = float(p.get("form", 0.0))
                    points = int(p.get("total_points", 0))
                    cost = p.get("now_cost", 0) / 10.0
                    
                    if cost >= 6.5 and points >= 25:
                        fixs = cls.get_player_upcoming_fixtures(p, count=1)
                        fdr = fixs[0]["fdr"] if fixs else 3
                        is_home = fixs[0]["is_home"] if fixs else False
                        opp = fixs[0]["opp_short"] if fixs else "OPP"
                        
                        # Score: Form * 1.5 + (5 - FDR) * 2 + (Home bonus 1.5)
                        score = (form * 1.6) + ((5.0 - fdr) * 2.2) + (1.5 if is_home else 0.0)
                        
                        # Bonus for Haaland/Salah/Palmer anchors
                        wname = p.get("web_name", "")
                        if wname in ["Haaland", "Salah", "Palmer", "Saka"]:
                            score += 3.0
                            
                        candidates.append({
                            "player": p,
                            "score": score,
                            "fdr": fdr,
                            "opp": opp,
                            "is_home": is_home,
                            "form": form,
                            "price": cost
                        })
                except Exception:
                    continue
                    
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top5 = candidates[:5]
        
        if not top5:
            return "عذراً، تعذر حساب ترشيحات الكابتن حالياً. يرجى المحاولة لاحقاً."
            
        ranks = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        lines = []
        for idx, item in enumerate(top5):
            p = item["player"]
            t_short = teams.get(p.get("team"), {}).get("short_name", "")
            ha = "على أرضه 🏟️" if item["is_home"] else "خارج أرضه ✈️"
            fdr_emoji = cls.format_fdr_emoji(item["fdr"])
            
            lines.append(
                f"{ranks[idx]} <b>{p.get('web_name')}</b> ({t_short} - £{item['price']:.1f}m)\n"
                f"   • الماتش: ضد <b>{item['opp']}</b> ({ha}) {fdr_emoji}\n"
                f"   • الفورمة: <b>{item['form']}</b> | مؤشر التألق: <b>{item['score']:.1f}/20</b>"
            )
            
        result = (
            f"👑 <b>أفضل خيارات الكابتن الموصى بها حسابياً لـ {gw_label}:</b>\n\n"
            + "\n\n".join(lines) + "\n\n"
            "💡 <i>التقييم يعتمد على: فورمة اللاعب، سهولة دفاع الخصم، ونسبة التسجيل المتوقعة داخل أو خارج الأرض.</i>"
        )
        return result

    @classmethod
    def get_team_analysis(cls, team_id: int) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        # 1. Fetch Entry Overview
        entry_data = _get_with_cache(FPL_ENTRY_URL.format(team_id=team_id), ttl=120)
        if not entry_data or "id" not in entry_data:
            return ("⚠️ لم نتمكن من العثور على فريق بهذا الرقم! تأكد من إدخال رقم الـ ID الصحيح لفريقك في الفانتسي.", None)
            
        team_name = entry_data.get("name", "فريقي")
        mgr_name = f"{entry_data.get('player_first_name', '')} {entry_data.get('player_last_name', '')}".strip()
        overall_pts = entry_data.get("summary_overall_points", 0)
        overall_rank = entry_data.get("summary_overall_rank", 0)
        gw_pts = entry_data.get("summary_event_points", 0)
        
        curr_ev = entry_data.get("current_event")
        if not curr_ev:
            curr, _ = cls.get_current_and_next_gw()
            curr_ev = curr.get("id") if curr else 1
            
        picks_data = None
        for try_gw in range(curr_ev, 0, -1):
            p_data = _get_with_cache(FPL_PICKS_URL.format(team_id=team_id, gw=try_gw), ttl=120)
            if p_data and "picks" in p_data and len(p_data.get("picks", [])) > 0:
                picks_data = p_data
                break
            
        if not picks_data or "picks" not in picks_data:
            return (f"✅ تم العثور على فريق <b>{team_name}</b> (المدرب: {mgr_name})، ولكن تشكيلة الجولة لم تكتمل بعد على خوادم البريميرليج.", entry_data)
            
        picks = picks_data.get("picks", [])
        players_dict = {p["id"]: p for p in cls.get_players_list()}
        teams_dict = cls.get_teams_dict()
        
        starting_xi = picks[:11]
        bench = picks[11:]
        
        captain_name = ""
        vice_name = ""
        injuries = []
        tough_fixtures = []
        starting_names = []
        
        for pick in starting_xi:
            pid = pick.get("element")
            p = players_dict.get(pid, {})
            wname = p.get("web_name", "لاعب")
            pos_id = p.get("element_type", 1)
            pos_emoji = POSITION_MAP.get(pos_id, {}).get("emoji", "⚽")
            starting_names.append(f"{pos_emoji} {wname}")
            
            if pick.get("is_captain"):
                captain_name = wname
            if pick.get("is_vice_captain"):
                vice_name = wname
                
            status = p.get("status", "a")
            if status != "a":
                injuries.append(f"• <b>{wname}</b> ({p.get('news', 'مشكوك في مشاركته')})")
                
            fixs = cls.get_player_upcoming_fixtures(p, count=1)
            if fixs and fixs[0]["fdr"] >= 4:
                t_opp = fixs[0]["opp_short"]
                tough_fixtures.append(f"• <b>{wname}</b> ضد {t_opp} {cls.format_fdr_emoji(fixs[0]['fdr'])}")
                
        # Calculate Team Health Score
        base_score = 95
        base_score -= (len(injuries) * 15)
        base_score -= (len(tough_fixtures) * 6)
        health_score = max(35, min(100, base_score))
        
        health_emoji = "🟢 ممتاز" if health_score >= 80 else ("🟡 متوسط" if health_score >= 60 else "🔴 يحتاج تدخل فوري")
        
        # Rank formatting
        rank_str = f"{overall_rank:,}" if overall_rank else "غير مصنف"
        
        report = (
            f"📋 <b>تقرير فحص وتقييم التشكيلة (Rate My Team):</b>\n\n"
            f"👤 المدرب: <b>{mgr_name}</b>\n"
            f"🛡️ اسم الفريق: <b>{team_name}</b> (ID: <code>{team_id}</code>)\n"
            f"🏆 إجمالي النقاط: <b>{overall_pts} نقطة</b> | الترتيب العام: <b>{rank_str}</b>\n\n"
            f"🩺 <b>مؤشر صحة وقوة التشكيلة:</b> <b>{health_score}/100</b> {health_emoji}\n"
            f"👑 الكابتن الحالي: <b>{captain_name}</b> | نائب الكابتن: <b>{vice_name}</b>\n\n"
        )
        
        if injuries:
            report += "🚨 <b>تحذيرات الغيابات والإصابات في الأساسيين:</b>\n" + "\n".join(injuries) + "\n\n"
        else:
            report += "✅ <b>الأساسيون جاهزون:</b> لا توجد أي إصابات معلنة في تشكيلتك الأساسية.\n\n"
            
        if tough_fixtures:
            report += "⚠️ <b>مواجهات صعبة تنتظر لاعبيك (FDR 4+):</b>\n" + "\n".join(tough_fixtures) + "\n\n"
            
        report += (
            "💡 <b>التوصية التكتيكية للجولة:</b>\n"
        )
        if injuries:
            report += "• يُنصح باستخدام التبديل المجاني فوراً لتعويض اللاعب المصاب قبل هبوط سعره.\n"
        elif tough_fixtures:
            report += "• تشكيلتك مستقرة، فكّر في تدوير الدكة للبدلاء الذين يملكون مواجهات أسهل.\n"
        else:
            report += "• تشكيلة ممتازة ومثالية جداً! يمكنك ترحيل التبديل المجاني (Roll Transfer) للجولة القادمة.\n"
            
        return (report, entry_data)

    @classmethod
    def get_price_change_predictions(cls) -> str:
        players = cls.get_players_list()
        teams = cls.get_teams_dict()
        
        # Sort by transfers_in_event and transfers_out_event
        risers = sorted(players, key=lambda x: x.get("transfers_in_event", 0), reverse=True)[:5]
        fallers = sorted(players, key=lambda x: x.get("transfers_out_event", 0), reverse=True)[:5]
        
        r_lines = []
        for p in risers:
            t = teams.get(p.get("team"), {}).get("short_name", "")
            price = p.get("now_cost", 0) / 10.0
            in_count = p.get("transfers_in_event", 0)
            r_lines.append(f"📈 <b>{p.get('web_name')}</b> ({t}) - £{price:.1f}m (دخل لـ {in_count:,} فريق)")
            
        f_lines = []
        for p in fallers:
            t = teams.get(p.get("team"), {}).get("short_name", "")
            price = p.get("now_cost", 0) / 10.0
            out_count = p.get("transfers_out_event", 0)
            f_lines.append(f"📉 <b>{p.get('web_name')}</b> ({t}) - £{price:.1f}m (باعه {out_count:,} فريق)")
            
        text = (
            "📊 <b>رادار حركة وانتقالات الأسعار اليومية (Price Watch):</b>\n\n"
            "🔥 <b>أكثر اللاعبين طلباً وشراءً (مرشحون لارتفاع السعر):</b>\n"
            + "\n".join(r_lines) + "\n\n"
            "❄️ <b>أكثر اللاعبين بيعاً وتخلصاً (مرشحون لانخفاض السعر):</b>\n"
            + "\n".join(f_lines) + "\n\n"
            "💡 <i>تحدث تغيرات الأسعار الرسمية يومياً في حدود الساعة 3:15 فجراً بتوقيت مصر.</i>"
        )
        return text

    @classmethod
    def compare_players(cls, name1: str, name2: str) -> str:
        p1 = cls.search_player(name1)
        p2 = cls.search_player(name2)
        
        if not p1 or not p2:
            return "⚠️ تعذر العثور على أحد اللاعبين! تأكد من كتابة الأسماء بشكل صحيح (مثال: بالمر ساكا أو Palmer Saka)."
            
        teams = cls.get_teams_dict()
        t1 = teams.get(p1.get("team"), {}).get("short_name", "")
        t2 = teams.get(p2.get("team"), {}).get("short_name", "")
        
        price1 = p1.get("now_cost", 0) / 10.0
        price2 = p2.get("now_cost", 0) / 10.0
        
        pts1 = p1.get("total_points", 0)
        pts2 = p2.get("total_points", 0)
        
        form1 = p1.get("form", "0.0")
        form2 = p2.get("form", "0.0")
        
        sel1 = p1.get("selected_by_percent", "0")
        sel2 = p2.get("selected_by_percent", "0")
        
        g1, a1 = p1.get("goals_scored", 0), p1.get("assists", 0)
        g2, a2 = p2.get("goals_scored", 0), p2.get("assists", 0)
        
        text = (
            f"⚔️ <b>مقارنة رأس برأس (Head-to-Head):</b>\n\n"
            f"🔵 <b>{p1.get('web_name')}</b> ({t1})  🆚  🔴 <b>{p2.get('web_name')}</b> ({t2})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 السعر: <b>£{price1:.1f}m</b>  🆚  <b>£{price2:.1f}m</b>\n"
            f"🏆 النقاط: <b>{pts1}</b>  🆚  <b>{pts2}</b>\n"
            f"🔥 الفورمة: <b>{form1}</b>  🆚  <b>{form2}</b>\n"
            f"👥 الملكية: <b>{sel1}%</b>  🆚  <b>{sel2}%</b>\n"
            f"⚽ الأهداف: <b>{g1}</b>  🆚  <b>{g2}</b>\n"
            f"🎯 الأسيست: <b>{a1}</b>  🆚  <b>{a2}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
        )
        if pts1 > pts2:
            text += f"🌟 <b>الأفضلية الحالية:</b> <b>{p1.get('web_name')}</b> متفوق في إجمالي النقاط والمردود التهديفي."
        elif pts2 > pts1:
            text += f"🌟 <b>الأفضلية الحالية:</b> <b>{p2.get('web_name')}</b> متفوق في إجمالي النقاط والمردود التهديفي."
        else:
            text += "⚖️ <b>النتيجة:</b> أرقام اللاعبين متقاربة جداً؛ الفيصل هو سهولة المباريات القادمة!"
            
        return text
