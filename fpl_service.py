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

    @classmethod
    def find_replacements(cls, pos_id: int, max_cost: float, exclude_ids: List[int] = None, top_n: int = 3) -> List[Dict[str, Any]]:
        if not exclude_ids:
            exclude_ids = []
        players = cls.get_players_list()
        candidates = []
        for p in players:
            if p["id"] in exclude_ids:
                continue
            if p.get("element_type") != pos_id:
                continue
            cost = p.get("now_cost", 0) / 10.0
            if cost > max_cost:
                continue
            if p.get("status") not in ["a", "d"]:
                continue
                
            try:
                form = float(p.get("form", 0.0))
                total_pts = int(p.get("total_points", 0))
                if total_pts < 10 and form < 2.0:
                    continue
                    
                fixs = cls.get_player_upcoming_fixtures(p, count=3)
                if not fixs:
                    continue
                fdr_avg = sum(f["fdr"] for f in fixs) / len(fixs)
                
                # Score: high form, low FDR, solid points baseline
                score = (form * 2.2) + (total_pts * 0.1) + ((5.0 - fdr_avg) * 3.5)
                candidates.append({
                    "player": p,
                    "score": score,
                    "cost": cost,
                    "form": form,
                    "total_pts": total_pts,
                    "fixs": fixs,
                    "fdr_avg": fdr_avg
                })
            except Exception:
                continue
                
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_n]

    @classmethod
    def get_team_transfers(cls, team_id: int) -> Tuple[str, Optional[Dict[str, Any]]]:
        entry_data = _get_with_cache(FPL_ENTRY_URL.format(team_id=team_id), ttl=120)
        if not entry_data or "id" not in entry_data:
            return ("⚠️ لم نتمكن من العثور على فريق بهذا الرقم! تأكد من إدخال رقم الـ ID الصحيح لفريقك في الفانتسي.", None)
            
        team_name = entry_data.get("name", "فريقي")
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
            return (f"✅ تم العثور على فريق <b>{team_name}</b> ولكن تشكيلة الجولة لم تكتمل بعد.", entry_data)
            
        bank = picks_data.get("entry_history", {}).get("bank", 0) / 10.0
        picks = picks_data.get("picks", [])
        team_player_ids = [p["element"] for p in picks]
        players_dict = {p["id"]: p for p in cls.get_players_list()}
        teams_dict = cls.get_teams_dict()
        
        # Score every player in team for SELL PRIORITY
        sell_candidates = []
        for pick in picks:
            pid = pick.get("element")
            p = players_dict.get(pid, {})
            if not p:
                continue
                
            status = p.get("status", "a")
            chance = p.get("chance_of_playing_next_round")
            form = float(p.get("form", 0.0))
            cost = p.get("now_cost", 0) / 10.0
            fixs = cls.get_player_upcoming_fixtures(p, count=3)
            fdr_avg = (sum(f["fdr"] for f in fixs) / len(fixs)) if fixs else 3.0
            
            urgency = 0
            reasons = []
            
            if status in ["i", "s", "u"]:
                urgency += 80
                reasons.append(p.get("news", "مصاب أو موقوف"))
            elif status == "d" or (chance is not None and chance <= 50):
                urgency += 50
                reasons.append(p.get("news", "شكوك قوية حول مشاركته"))
            elif fdr_avg >= 3.6:
                urgency += 25
                reasons.append(f"مباريات قادمة صعبة (متوسط صعوبة {fdr_avg:.1f})")
                
            if form < 2.0 and cost >= 6.0:
                urgency += 20
                reasons.append(f"تراجع حاد في الفورمة ({form})")
                
            sell_candidates.append({
                "player": p,
                "urgency": urgency,
                "reasons": reasons,
                "cost": cost,
                "pos_id": p.get("element_type", 1),
                "fdr_avg": fdr_avg
            })
            
        sell_candidates.sort(key=lambda x: x["urgency"], reverse=True)
        worst = sell_candidates[0] if sell_candidates else None
        
        if not worst or (worst["urgency"] == 0 and worst["fdr_avg"] <= 3.0):
            worst = min(sell_candidates, key=lambda x: float(x["player"].get("form", 0.0)))
            
        sell_player = worst["player"]
        sell_cost = worst["cost"]
        pos_id = worst["pos_id"]
        pos_info = POSITION_MAP.get(pos_id, {"name": "لاعب", "emoji": "⚽"})
        sell_team = teams_dict.get(sell_player.get("team"), {}).get("short_name", "")
        sell_reasons = " ، ".join(worst["reasons"]) if worst["reasons"] else "انخفاض المردود الهجومي/الدفاعي مؤخراً"
        
        # Available budget
        max_buy_budget = round(sell_cost + bank, 1)
        
        # Find top replacements
        buys = cls.find_replacements(
            pos_id=pos_id,
            max_cost=max_buy_budget,
            exclude_ids=team_player_ids,
            top_n=3
        )
        
        text = (
            f"🔄 <b>توصيات التبديلات الذكية لفريقك (Transfer Advisor):</b>\n\n"
            f"🛡️ الفريق: <b>{team_name}</b> | الميزانية في البنك: <b>£{bank:.1f}m</b>\n\n"
            f"🔴 <b>اللاعب الأكثر ترشيحاً للبيع (Sell Priority):</b>\n"
            f"• {pos_info['emoji']} <b>{sell_player.get('web_name')}</b> ({sell_team} - £{sell_cost:.1f}m)\n"
            f"⚠️ <b>سبب البيع:</b> {sell_reasons}\n"
            f"💰 ميزانيتك المتاحة للشراء مكانه: <b>£{max_buy_budget:.1f}m</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🟢 <b>أفضل 3 بدلاء مقترحين للشراء مكانه (Buy Options):</b>\n\n"
        )
        
        if buys:
            ranks = ["1️⃣", "2️⃣", "3️⃣"]
            for i, b in enumerate(buys):
                bp = b["player"]
                bt = teams_dict.get(bp.get("team"), {}).get("short_name", "")
                fix_strs = []
                for fx in b["fixs"]:
                    ha = "H" if fx["is_home"] else "A"
                    fix_strs.append(f"{fx['opp_short']}({ha}) {cls.format_fdr_emoji(fx['fdr'])}")
                fix_text = " | ".join(fix_strs)
                savings = round(max_buy_budget - b["cost"], 1)
                sav_str = f"(يوفر £{savings:.1f}m في البنك)" if savings > 0 else "(يستغل كامل الميزانية)"
                
                text += (
                    f"{ranks[i]} <b>{bp.get('web_name')}</b> ({bt} - £{b['cost']:.1f}m) {sav_str}\n"
                    f"   • الفورمة: <b>{b['form']}</b> | إجمالي النقاط: <b>{b['total_pts']}</b>\n"
                    f"   • المباريات الـ 3 القادمة: {fix_text}\n\n"
                )
        else:
            text += "لا يوجد بدلاء مميزين في حدود هذه الميزانية حالياً، فكّر في ترحيل التبديل.\n\n"
            
        text += "💡 <i>الخوارزمية تفحص: نسبة الإصابات، سهولة جدول المباريات الـ 3 القادمة (FDR)، والفورمة التهديفية.</i>"
        return (text, entry_data)

    @classmethod
    def find_player_swap(cls, player_name: str) -> str:
        p = cls.search_player(player_name)
        if not p:
            return f"⚠️ تعذر العثور على لاعب باسم: {player_name}"
            
        pos_id = p.get("element_type", 1)
        pos_info = POSITION_MAP.get(pos_id, {"name": "لاعب", "emoji": "⚽"})
        cost = p.get("now_cost", 0) / 10.0
        teams_dict = cls.get_teams_dict()
        t_short = teams_dict.get(p.get("team"), {}).get("short_name", "")
        
        # Search for replacements up to player price + 0.5
        max_cost = cost + 0.5
        buys = cls.find_replacements(pos_id=pos_id, max_cost=max_cost, exclude_ids=[p["id"]], top_n=3)
        
        text = (
            f"🔄 <b>أفضل البدلاء المقترحين للاعب {p.get('web_name')}:</b>\n\n"
            f"🔴 اللاعب المراد استبداله: {pos_info['emoji']} <b>{p.get('web_name')}</b> ({t_short} - £{cost:.1f}m)\n\n"
            f"🟢 <b>أفضل 3 خيارات شراء في نفس المركز والحدود السعرية:</b>\n\n"
        )
        if buys:
            ranks = ["1️⃣", "2️⃣", "3️⃣"]
            for i, b in enumerate(buys):
                bp = b["player"]
                bt = teams_dict.get(bp.get("team"), {}).get("short_name", "")
                fix_strs = []
                for fx in b["fixs"]:
                    ha = "H" if fx["is_home"] else "A"
                    fix_strs.append(f"{fx['opp_short']}({ha}) {cls.format_fdr_emoji(fx['fdr'])}")
                fix_text = " | ".join(fix_strs)
                
                text += (
                    f"{ranks[i]} <b>{bp.get('web_name')}</b> ({bt} - £{b['cost']:.1f}m)\n"
                    f"   • الفورمة: <b>{b['form']}</b> | النقاط: <b>{b['total_pts']}</b>\n"
                    f"   • المباريات القادمة: {fix_text}\n\n"
                )
        else:
            text += "لا يوجد بدلاء مميزين في حدود هذه الميزانية حالياً.\n\n"
            
        return text

    @classmethod
    def get_differentials(cls, top_n: int = 4) -> str:
        players = cls.get_players_list()
        teams = cls.get_teams_dict()
        curr, next_ev = cls.get_current_and_next_gw()
        gw_label = next_ev.get("name") if next_ev else (curr.get("name") if curr else "الجولة")
        
        candidates = []
        for p in players:
            if p.get("status") != "a":
                continue
            try:
                ownership = float(p.get("selected_by_percent", 0.0))
                if ownership >= 10.0 or ownership < 0.5:
                    continue
                form = float(p.get("form", 0.0))
                if form < 2.5:
                    continue
                cost = p.get("now_cost", 0) / 10.0
                pts = int(p.get("total_points", 0))
                
                fixs = cls.get_player_upcoming_fixtures(p, count=3)
                if not fixs:
                    continue
                fdr_avg = sum(f["fdr"] for f in fixs) / len(fixs)
                
                score = (form * 2.5) + ((5.0 - fdr_avg) * 3.0) + ((10.0 - ownership) * 0.5) + (pts * 0.1)
                candidates.append({
                    "player": p,
                    "score": score,
                    "ownership": ownership,
                    "form": form,
                    "cost": cost,
                    "pts": pts,
                    "fixs": fixs,
                    "fdr_avg": fdr_avg
                })
            except Exception:
                continue
                
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top_diffs = candidates[:top_n]
        
        if not top_diffs:
            return "لا تتوفر ترشيحات ديفرينشال حالياً."
            
        text = (
            f"💎 <b>رادار اللاعبين الـ Differential لـ {gw_label}:</b>\n\n"
            "🎯 <i>لاعيبة سحرية نسبة ملكيتهم أقل من 10% وجدولهم سهل، عشان تفرق عن منافسيك في الترتيب:</i>\n\n"
        )
        
        for i, d in enumerate(top_diffs):
            p = d["player"]
            t = teams.get(p.get("team"), {}).get("short_name", "")
            pos_info = POSITION_MAP.get(p.get("element_type", 1), {"emoji": "⚽", "name": "لاعب"})
            fix_strs = []
            for fx in d["fixs"]:
                ha = "H" if fx["is_home"] else "A"
                fix_strs.append(f"{fx['opp_short']}({ha}) {cls.format_fdr_emoji(fx['fdr'])}")
            fix_text = " | ".join(fix_strs)
            
            text += (
                f"✨ <b>{p.get('web_name')}</b> ({t} - £{d['cost']:.1f}m) [{pos_info['emoji']} {pos_info['name']}]\n"
                f"   • نسبة الملكية: <b>{d['ownership']}% فقط! 🤫</b>\n"
                f"   • الفورمة: <b>{d['form']}</b> | النقاط: <b>{d['pts']}</b>\n"
                f"   • المباريات القادمة: {fix_text}\n\n"
            )
        return text

    @classmethod
    def calculate_hit(cls, sell_name: str, buy_name: str) -> str:
        p_sell = cls.search_player(sell_name)
        p_buy = cls.search_player(buy_name)
        
        if not p_sell or not p_buy:
            return "⚠️ تعذر العثور على أحد اللاعبين! تأكد من كتابة الاسمين بشكل صحيح (مثال: <code>/hit اكانجي جابرييل</code> أو <code>/hit Eze Palmer</code>)."
            
        teams = cls.get_teams_dict()
        t_sell = teams.get(p_sell.get("team"), {}).get("short_name", "")
        t_buy = teams.get(p_buy.get("team"), {}).get("short_name", "")
        
        fixs_sell = cls.get_player_upcoming_fixtures(p_sell, count=2)
        fixs_buy = cls.get_player_upcoming_fixtures(p_buy, count=2)
        
        fdr_sell = (sum(f["fdr"] for f in fixs_sell) / len(fixs_sell)) if fixs_sell else 3.0
        fdr_buy = (sum(f["fdr"] for f in fixs_buy) / len(fixs_buy)) if fixs_buy else 3.0
        
        form_sell = float(p_sell.get("form", 0.0))
        form_buy = float(p_buy.get("form", 0.0))
        
        status_sell = p_sell.get("status", "a")
        sell_penalty = -3.0 if status_sell != "a" else 0.0
        
        xp_sell = max(1.0, (form_sell * 1.5) + ((5.0 - fdr_sell) * 1.2) + sell_penalty)
        xp_buy = max(2.0, (form_buy * 1.6) + ((5.0 - fdr_buy) * 1.8))
        
        net_gain = round(xp_buy - xp_sell - 4.0, 1)
        
        text = (
            "🧮 <b>حاسبة قرار التبديل بالسالب (-4 Hit Calculator):</b>\n\n"
            f"🔴 بيع: <b>{p_sell.get('web_name')}</b> ({t_sell}) | نقاط متوقعة للجولتين: ~{xp_sell:.1f}\n"
            f"🟢 شراء: <b>{p_buy.get('web_name')}</b> ({t_buy}) | نقاط متوقعة للجولتين: ~{xp_buy:.1f}\n"
            f"⚡ خصم التبديل الإضافي: <b>-4 نقاط</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>صافي الفارق المتوقع بعد خصم الـ 4 نقاط:</b> "
        )
        
        if net_gain >= 1.5:
            text += (
                f"<b>+{net_gain} نقطة لصالحك! 🟢</b>\n\n"
                "✅ <b>القرار الموصى به: نعم، يستاهل تعمل سالب 4!</b>\n"
                f"مكسب النقاط المتوقع من {p_buy.get('web_name')} يغطي خصم السالب وزيادة واضحة، خصوصاً مع تفوق الفورمة وسهولة الماتشات."
            )
        elif net_gain >= -1.0:
            text += (
                f"<b>{net_gain} نقطة 🟡</b>\n\n"
                "⚠️ <b>القرار الموصى به: قرار محايد ومخاطرة متساوية.</b>\n"
                "الفارق متقارب جداً. إذا كان اللاعب القديم غير مصاب وقادر على اللعب، يفضل ترحيل التبديل للجولة القادمة مجاناً."
            )
        else:
            text += (
                f"<b>{net_gain} نقطة (خسارة) 🔴</b>\n\n"
                "⛔ <b>القرار الموصى به: لا يُنصح بالسالب إطلاقاً!</b>\n"
                "المجازفة بالسالب غير مبررة وستخصم من رصيدك دون تعويض مؤكد في النقاط."
            )
            
        return text

    @classmethod
    def get_wildcard_squad(cls) -> str:
        players = cls.get_players_list()
        teams = cls.get_teams_dict()
        curr, next_ev = cls.get_current_and_next_gw()
        gw_label = next_ev.get("name") if next_ev else (curr.get("name") if curr else "الجولة")
        
        def get_best_in_pos(pos, min_c, max_c, exclude_teams=None, exclude_pids=None, req_names=None):
            if not exclude_teams: exclude_teams = {}
            if not exclude_pids: exclude_pids = set()
            cands = []
            for p in players:
                if p["id"] in exclude_pids: continue
                if p.get("element_type") != pos: continue
                cost = p.get("now_cost", 0) / 10.0
                if not (min_c <= cost <= max_c): continue
                if p.get("status") not in ["a", "d"]: continue
                t_id = p.get("team")
                if exclude_teams.get(t_id, 0) >= 3: continue
                
                form = float(p.get("form", 0.0))
                pts = int(p.get("total_points", 0))
                fixs = cls.get_player_upcoming_fixtures(p, count=3)
                fdr_avg = sum(f["fdr"] for f in fixs) / len(fixs) if fixs else 3.0
                
                wname = p.get("web_name", "")
                score = (form * 2.0) + (pts * 0.1) + ((5.0 - fdr_avg) * 3.0)
                if req_names and wname in req_names:
                    score += 10.0
                cands.append({"player": p, "score": score, "cost": cost})
            cands.sort(key=lambda x: x["score"], reverse=True)
            return cands[0]["player"] if cands else None

        team_counts = {}
        chosen_ids = set()
        
        haaland = cls.search_player("Haaland")
        pedro = cls.search_player("João Pedro") or cls.search_player("Pedro")
        
        gk1 = get_best_in_pos(1, 4.5, 5.5, team_counts, chosen_ids, ["Raya", "Alisson", "Pickford"])
        if gk1: chosen_ids.add(gk1["id"]); team_counts[gk1["team"]] = team_counts.get(gk1["team"], 0) + 1
        gk2 = get_best_in_pos(1, 4.0, 4.0, team_counts, chosen_ids)
        if gk2: chosen_ids.add(gk2["id"])
        
        def1 = get_best_in_pos(2, 5.5, 6.5, team_counts, chosen_ids, ["Gabriel", "Calafiori", "Gvardiol", "Alexander-Arnold"])
        if def1: chosen_ids.add(def1["id"]); team_counts[def1["team"]] = team_counts.get(def1["team"], 0) + 1
        def2 = get_best_in_pos(2, 4.5, 5.5, team_counts, chosen_ids)
        if def2: chosen_ids.add(def2["id"]); team_counts[def2["team"]] = team_counts.get(def2["team"], 0) + 1
        def3 = get_best_in_pos(2, 4.5, 5.0, team_counts, chosen_ids)
        if def3: chosen_ids.add(def3["id"]); team_counts[def3["team"]] = team_counts.get(def3["team"], 0) + 1
        def4 = get_best_in_pos(2, 4.0, 4.5, team_counts, chosen_ids)
        if def4: chosen_ids.add(def4["id"]); team_counts[def4["team"]] = team_counts.get(def4["team"], 0) + 1
        def5 = get_best_in_pos(2, 4.0, 4.0, team_counts, chosen_ids)
        if def5: chosen_ids.add(def5["id"])
        
        mid1 = get_best_in_pos(3, 9.0, 11.0, team_counts, chosen_ids, ["Palmer", "Saka", "Salah", "Foden"])
        if mid1: chosen_ids.add(mid1["id"]); team_counts[mid1["team"]] = team_counts.get(mid1["team"], 0) + 1
        mid2 = get_best_in_pos(3, 7.5, 9.0, team_counts, chosen_ids, ["Cherki", "Mbeumo", "Rogers"])
        if mid2: chosen_ids.add(mid2["id"]); team_counts[mid2["team"]] = team_counts.get(mid2["team"], 0) + 1
        mid3 = get_best_in_pos(3, 6.5, 7.5, team_counts, chosen_ids)
        if mid3: chosen_ids.add(mid3["id"]); team_counts[mid3["team"]] = team_counts.get(mid3["team"], 0) + 1
        mid4 = get_best_in_pos(3, 5.5, 6.5, team_counts, chosen_ids)
        if mid4: chosen_ids.add(mid4["id"]); team_counts[mid4["team"]] = team_counts.get(mid4["team"], 0) + 1
        mid5 = get_best_in_pos(3, 4.5, 5.5, team_counts, chosen_ids)
        if mid5: chosen_ids.add(mid5["id"])
        
        fwd1 = haaland if haaland else get_best_in_pos(4, 12.0, 16.0)
        if fwd1: chosen_ids.add(fwd1["id"]); team_counts[fwd1["team"]] = team_counts.get(fwd1["team"], 0) + 1
        fwd2 = pedro if pedro else get_best_in_pos(4, 7.0, 8.5)
        if fwd2: chosen_ids.add(fwd2["id"]); team_counts[fwd2["team"]] = team_counts.get(fwd2["team"], 0) + 1
        fwd3 = get_best_in_pos(4, 5.0, 6.5, team_counts, chosen_ids)
        if fwd3: chosen_ids.add(fwd3["id"])
        
        starters = [gk1, def1, def2, def3, mid1, mid2, mid3, mid4, fwd1, fwd2, fwd3]
        bench = [gk2, def4, def5, mid5]
        all_p = [p for p in starters + bench if p]
        total_cost = sum(p.get("now_cost", 0) for p in all_p) / 10.0
        
        def fmt_p(p):
            t = teams.get(p.get("team"), {}).get("short_name", "")
            c = p.get("now_cost", 0) / 10.0
            return f"• <b>{p.get('web_name')}</b> ({t} - £{c:.1f}m)"

        text = (
            f"🃏 <b>تشكيلة الـ Wildcard المثالية بالذكاء الاصطناعي لـ {gw_label}:</b>\n\n"
            f"💰 إجمالي تكلفة التشكيلة: <b>£{total_cost:.1f}m</b> / 100.0m\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏆 <b>التشكيل الأساسي الموصى به (3-4-3):</b>\n\n"
            f"🧤 <b>حراسة المرمى:</b>\n{fmt_p(gk1) if gk1 else ''}\n\n"
            f"🛡️ <b>خط الدفاع:</b>\n" + "\n".join([fmt_p(p) for p in [def1, def2, def3] if p]) + "\n\n"
            f"🎯 <b>خط الوسط:</b>\n" + "\n".join([fmt_p(p) for p in [mid1, mid2, mid3, mid4] if p]) + "\n\n"
            f"⚽ <b>خط الهجوم:</b>\n" + "\n".join([fmt_p(p) for p in [fwd1, fwd2, fwd3] if p]) + "\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🪑 <b>مقاعد البدلاء (Bench):</b>\n" + "\n".join([fmt_p(p) for p in bench if p]) + "\n\n"
            f"👑 <b>الكابتن المقترح:</b> <b>{fwd1.get('web_name') if fwd1 else (mid1.get('web_name') if mid1 else 'Haaland')}</b>\n"
            "💡 <i>التشكيلة مبنية رياضياً على أعلى سقف نقاط متوقع للفورمة وسهولة الجولات الـ 5 القادمة.</i>"
        )
        return text

    @classmethod
    def get_set_piece_takers(cls, team_name_query: str = None) -> str:
        players = cls.get_players_list()
        teams = cls.get_teams_dict()
        
        target_team_id = None
        target_team_name = None
        if team_name_query:
            q = team_name_query.strip().lower()
            for tid, t in teams.items():
                if q in t.get("name", "").lower() or q in t.get("short_name", "").lower():
                    target_team_id = tid
                    target_team_name = t.get("name")
                    break
                    
        if target_team_id:
            t_players = [p for p in players if p.get("team") == target_team_id]
            pens = sorted([p for p in t_players if p.get("penalties_order")], key=lambda x: x["penalties_order"])
            fk = sorted([p for p in t_players if p.get("direct_freekicks_order")], key=lambda x: x["direct_freekicks_order"])
            corners = sorted([p for p in t_players if p.get("corners_and_indirect_freekicks_order")], key=lambda x: x["corners_and_indirect_freekicks_order"])
            
            text = f"🎯 <b>مسددو الكرات الثابتة لنادي {target_team_name}:</b>\n\n"
            text += "⚽ <b>ضربات الجزاء (Penalties):</b>\n" + ("\n".join([f"  {p['penalties_order']}. <b>{p.get('web_name')}</b>" for p in pens[:2]]) if pens else "  غير محدد رسمياً") + "\n\n"
            text += "🚀 <b>الضربات الحرة المباشرة (Free Kicks):</b>\n" + ("\n".join([f"  {p['direct_freekicks_order']}. <b>{p.get('web_name')}</b>" for p in fk[:2]]) if fk else "  غير محدد") + "\n\n"
            text += "📐 <b>الركنيات والرفعات (Corners):</b>\n" + ("\n".join([f"  {p['corners_and_indirect_freekicks_order']}. <b>{p.get('web_name')}</b>" for p in corners[:2]]) if corners else "  غير محدد") + "\n"
            return text
        else:
            lines = []
            for tid, t in sorted(teams.items(), key=lambda x: x[1]["name"]):
                p_pk = [p for p in players if p.get("team") == tid and p.get("penalties_order") == 1]
                pk_name = p_pk[0].get("web_name") if p_pk else "متغير"
                lines.append(f"• <b>{t['short_name']}</b>: {pk_name}")
                
            text = (
                "🎯 <b>مسددو ضربات الجزاء الرسميون في الدوري الإنجليزي:</b>\n\n"
                + "\n".join(lines)
                + "\n\n💡 <i>لمعرفة مسددي الفاولات والركنيات لنادي معين، اكتب: <code>/setpiece Arsenal</code> أو <code>/setpiece Chelsea</code></i>"
            )
            return text

    @classmethod
    def get_budget_rotation_pairs(cls) -> str:
        teams = cls.get_teams_dict()
        players = cls.get_players_list()
        
        budget_defs = [p for p in players if p.get("element_type") == 2 and p.get("now_cost", 0) <= 46 and p.get("status") == "a" and int(p.get("total_points", 0)) >= 15]
        budget_defs.sort(key=lambda x: float(x.get("form", 0.0)), reverse=True)
        
        d1 = budget_defs[0] if budget_defs else None
        d2 = None
        if d1:
            for d in budget_defs[1:]:
                if d.get("team") != d1.get("team"):
                    d2 = d
                    break
                    
        if not d1 or not d2:
            return "لا تتوفر بيانات كافية لثنائيات التدوير حالياً."
            
        t1 = teams.get(d1.get("team"), {}).get("short_name", "")
        t2 = teams.get(d2.get("team"), {}).get("short_name", "")
        c1 = d1.get("now_cost", 0) / 10.0
        c2 = d2.get("now_cost", 0) / 10.0
        
        fixs1 = cls.get_player_upcoming_fixtures(d1, count=4)
        fixs2 = cls.get_player_upcoming_fixtures(d2, count=4)
        
        lines = []
        for i in range(min(len(fixs1), len(fixs2))):
            f1 = fixs1[i]
            f2 = fixs2[i]
            better = d1 if f1["fdr"] <= f2["fdr"] else d2
            better_f = f1 if f1["fdr"] <= f2["fdr"] else f2
            ha = "H" if better_f["is_home"] else "A"
            lines.append(f"• GW{better_f['event']}: العب بـ <b>{better.get('web_name')}</b> ضد {better_f['opp_short']}({ha}) {cls.format_fdr_emoji(better_f['fdr'])}")
            
        text = (
            "🛡️ <b>أفضل ثنائي دفاعي رخيص للتدوير (Budget Rotation Pair):</b>\n\n"
            f"1️⃣ <b>{d1.get('web_name')}</b> ({t1} - £{c1:.1f}m)\n"
            f"2️⃣ <b>{d2.get('web_name')}</b> ({t2} - £{c2:.1f}m)\n"
            f"💰 التكلفة الإجمالية للثنائي: <b>£{(c1+c2):.1f}m فقط!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🗓️ <b>جدول تدوير الأساسي لكل جولة (العب بالأسهل بينهم):</b>\n\n"
            + "\n".join(lines)
            + "\n\n💡 <i>الفكرة: توفير ميزانية خط الوسط والهجوم باللعب دائماً بالمدافع صاحب المواجهة الأسهل.</i>"
        )
        return text

    @classmethod
    def get_league_info(cls, league_code: str = "", league_id: Optional[int] = None) -> Tuple[str, Optional[str]]:
        if not league_code:
            text = (
                "🏆 <b>دوري بوت الفانتسي الرسمي (FPL Assistant Bot League)</b>\n\n"
                "🔥 يتم حالياً تجهيز كود الدوري الرسمي لمستخدمي البوت للتنافس طوال الموسم!\n\n"
                "💡 <i>المشرف يستطيع تفعيل الكود عبر أمر: <code>/setleague CODE</code></i>"
            )
            return text, None

        join_url = f"https://fantasy.premierleague.com/leagues/auto-join/{league_code}"
        
        standings_text = ""
        league_title = "دوري مساعد الفانتسي الرسمي 🏆"
        
        if league_id:
            url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/"
            data = _get_with_cache(url, ttl=300)
            if data and "league" in data and "standings" in data:
                l_info = data["league"]
                league_title = l_info.get("name", league_title)
                results = data["standings"].get("results", [])
                
                if results:
                    standings_text = f"\n\n📊 <b>أوائل ترتيب الدوري حالياً (Top 5):</b>\n"
                    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                    for idx, r in enumerate(results[:5]):
                        medal = medals[idx] if idx < len(medals) else f"{idx+1}."
                        standings_text += f"{medal} <b>{r.get('entry_name')}</b> ({r.get('player_name')}) — <b>{r.get('total')}</b> نقطة\n"

        text = (
            f"🏆 <b>{league_title}</b>\n\n"
            f"🔑 <b>كود الدوري (League Code):</b>\n"
            f"<code>{league_code}</code> <i>(اضغط عليه لنسخه)</i>\n\n"
            "📲 <b>طريقة الانضمام السريعة:</b>\n"
            f"1. اضغط على زر <b>'انضم للدوري مباشرة'</b> بالأسفل.\n"
            "2. أو افتح موقع/تطبيق الفانتسي ⬅️ Leagues & Cup ⬅️ Join League ⬅️ الصق الكود أعلاه."
            f"{standings_text}\n\n"
            "⚽ <i>نافس باقي مستخدمي البوت واثبت أنك المدرب الأفضل هذا الموسم!</i>"
        )
        return text, join_url

