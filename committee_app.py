import streamlit as st
import gspread
import urllib.parse
import json
import os
import hashlib
import random
from datetime import datetime, timezone, timedelta

PK_TIME = timezone(timedelta(hours=5))
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1XD8zyf2LB0Su41CchdaNfwim4e8qbfNFMRokk3slUCA/edit?gid=2020970725#gid=2020970725"

st.set_page_config(page_title="Smart Committee (BC) System", page_icon="🤝", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

def make_hash(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

@st.cache_resource
def get_spreadsheet():
    if os.path.exists("credentials.json"):
        client = gspread.service_account(filename="credentials.json")
        url = DEFAULT_SHEET_URL
    else:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        client = gspread.service_account_from_dict(creds_dict)
        url = st.secrets.get("committee_sheet_url", DEFAULT_SHEET_URL)
    return client.open_by_url(url)

try:
    sheet = get_spreadsheet()
except Exception as e:
    st.error(f"گوگل شیٹ سے رابطہ نہیں ہو سکا: {e}")
    st.stop()

if "role" not in st.session_state:
    st.session_state.role = None
    st.session_state.user_id = ""
    st.session_state.admin_id = ""
    st.session_state.display_name = ""
    st.session_state.c_page = "home"

# --- لاگ ان اسکرین (ایڈمن اور ممبر دونوں کے لیے) ---
if st.session_state.role is None:
    st.title("🤝 اسمارٹ کمیٹی (BC) مینجمنٹ سسٹم")
    st.caption("ورژن 1.0 | مکمل شفاف اور خودکار کمیٹی ریکارڈ")

    login_tab1, login_tab2 = st.tabs(["👑 کمیٹی ایڈمن لاگ ان", "👤 ممبر پورٹل لاگ ان"])

    with login_tab1:
        with st.form("admin_login_form"):
            a_user = st.text_input("ایڈمن یوزر نیم:").strip()
            a_pass = st.text_input("ایڈمن پاس ورڈ:", type="password").strip()
            a_btn = st.form_submit_button("🔐 ایڈمن لاگ ان کریں")
            if a_btn:
                if a_user and a_pass:
                    h_pass = make_hash(a_pass)
                    admins_ws = sheet.worksheet("Admins")
                    all_admins = admins_ws.get_all_records()
                    found = False
                    for r in all_admins:
                        if str(r.get("admin_user")).strip() == a_user and str(r.get("password")).strip() == h_pass:
                            if str(r.get("status")).strip().lower() == "active":
                                st.session_state.role = "admin"
                                st.session_state.user_id = a_user
                                st.session_state.admin_id = a_user
                                st.session_state.display_name = r.get("committee_name", a_user)
                                found = True
                                st.rerun()
                            else:
                                st.error("آپ کا ایڈمن اکاؤنٹ فی الحال معطل ہے۔")
                                found = True
                                break
                    if not found:
                        st.error("غلط ایڈمن یوزر نیم یا پاس ورڈ!")
                else:
                    st.warning("یوزر نیم اور پاس ورڈ دونوں درج کریں۔")

    with login_tab2:
        st.info("اپنے کمیٹی ایڈمن سے حاصل کردہ یوزر نیم اور پاس ورڈ درج کریں۔")
        with st.form("member_login_form"):
            m_user = st.text_input("ممبر یوزر نیم:").strip()
            m_pass = st.text_input("ممبر پاس ورڈ:", type="password").strip()
            m_btn = st.form_submit_button("🔐 ممبر لاگ ان کریں")
            if m_btn:
                if m_user and m_pass:
                    h_pass = make_hash(m_pass)
                    mem_ws = sheet.worksheet("Members")
                    all_mems = mem_ws.get_all_records()
                    found = False
                    for r in all_mems:
                        if str(r.get("member_user")).strip() == m_user and str(r.get("password")).strip() == h_pass:
                            st.session_state.role = "member"
                            st.session_state.user_id = m_user
                            st.session_state.admin_id = str(r.get("admin_user")).strip()
                            st.session_state.display_name = r.get("member_name", m_user)
                            found = True
                            st.rerun()
                    if not found:
                        st.error("غلط ممبر یوزر نیم یا پاس ورڈ!")
                else:
                    st.warning("یوزر نیم اور پاس ورڈ دونوں درج کریں۔")

    st.divider()
    st.subheader("📝 اپنی کمیٹی چلانے کے لیے نیا ایڈمن اکاؤنٹ بنوائیں")
    st.info("""
    💳 **رجسٹریشن فیس ادائیگی (JazzCash / EasyPaisa):**
    * **اکاؤنٹ نمبر:** `0320-2609659` | **نام:** `Muhammad Younis` | **فیس:** `200 روپے`
    """)
    with st.form("req_admin_form"):
        ro_name = st.text_input("آپ کا پورا نام (لازمی):")
        rc_name = st.text_input("کمیٹی / گروپ کا نام (لازمی):")
        ro_phone = st.text_input("واٹس ایپ نمبر (لازمی):")
        ro_tid = st.text_input("ٹرانزیکشن آئی ڈی (TID):")
        ro_ss = st.file_uploader("یا فیس کی رسید اپ لوڈ کریں:", type=["png", "jpg", "jpeg"])
        if st.form_submit_button("✅ ایڈمن اکاؤنٹ کی درخواست بھیجیں"):
            if ro_name.strip() and rc_name.strip() and ro_phone.strip() and (ro_tid.strip() or ro_ss is not None):
                req_ws = sheet.worksheet("Admin_Requests")
                now_pk = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                pay_txt = f"TID: {ro_tid.strip()} | {'Screenshot Attached' if ro_ss else 'TID Only'}"
                req_ws.append_row([ro_name.strip(), rc_name.strip(), ro_phone.strip(), pay_txt, now_pk])
                st.success("🎉 درخواست موصول ہو گئی ہے! تصدیق کے بعد جلد ہی آپ کا ایڈمن اکاؤنٹ فعال کر دیا جائے گا۔")
            else:
                st.error("تمام ضروری خانے اور فیس کی تفصیل درج کریں۔")
    st.stop()
admins_ws = sheet.worksheet("Admins")
mem_ws = sheet.worksheet("Members")
pay_ws = sheet.worksheet("Payments")
draw_ws = sheet.worksheet("Draw_Results")

all_admins_rows = admins_ws.get_all_values()
admin_row_idx = None
admin_info = {}
for idx, r in enumerate(all_admins_rows[1:], start=2):
    if len(r) >= 11 and r[0].strip() == st.session_state.admin_id:
        admin_row_idx = idx
        admin_info = {
            "admin_user": r[0].strip(),
            "committee_name": r[2].strip(),
            "city": r[3].strip(),
            "acc_title": r[4].strip(),
            "acc_number": r[5].strip(),
            "period_days": int(float(r[6])) if r[6].strip() else 30,
            "total_members": int(float(r[7])) if r[7].strip() else 10,
            "inst_amount": float(r[8]) if r[8].strip() else 5000.0,
            "draw_mode": r[9].strip() if r[9].strip() else "ماہانہ قرعہ اندازی"
        }
        break

# === 1. ایڈمن پورٹل ===
if st.session_state.role == "admin":
    st.title(f"👑 {admin_info.get('committee_name', 'کمیٹی ایڈمن')}")
    st.caption(f"ایڈمن آئی ڈی: {st.session_state.user_id} | ورژن 1.0")

    if st.session_state.c_page != "home":
        if st.button("🏠 مین ڈیش بورڈ پر واپس جائیں", use_container_width=True):
            st.session_state.c_page = "home"
            st.rerun()
        st.divider()

    if st.session_state.c_page == "home":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⚙️\n\nکمیٹی سیٹنگز و\nاسمارٹ کیلکولیٹر", use_container_width=True):
                st.session_state.c_page = "settings"
                st.rerun()
            st.write("")
            if st.button("💰\n\nقسط وصولی و\nTID تصدیق", use_container_width=True):
                st.session_state.c_page = "payments"
                st.rerun()
        with c2:
            if st.button("👥\n\nممبران شامل کریں\nو پاس ورڈ بنائیں", use_container_width=True):
                st.session_state.c_page = "members"
                st.rerun()
            st.write("")
            if st.button("🎲\n\nکمیٹی کھولیں\n(قرعہ اندازی رزلٹ)", use_container_width=True):
                st.session_state.c_page = "draw"
                st.rerun()

        st.divider()
        _, l_col = st.columns([3, 1])
        with l_col:
            if st.button("🚪 لاگ آؤٹ", use_container_width=True):
                st.session_state.role = None
                st.session_state.c_page = "home"
                st.rerun()

    # صفحہ 1: سیٹنگز اور اسمارٹ کیلکولیٹر
    elif st.session_state.c_page == "settings":
        st.header("⚙️ کمیٹی سیٹنگز و خودکار حساب کتاب")
        with st.form("admin_settings_form"):
            c_name = st.text_input("کمیٹی کا نام:", value=admin_info["committee_name"])
            c_city = st.text_input("علاقہ / شہر:", value=admin_info["city"])
            acc_title = st.text_input("آپ کا اکاؤنٹ ٹائٹل (نام):", value=admin_info["acc_title"])
            acc_num = st.text_input("JazzCash / EasyPaisa نمبر:", value=admin_info["acc_number"])
            
            period_opt = st.selectbox("کمیٹی کھلنے کا وقفہ منتخب کریں:", [10, 20, 30], index=[10, 20, 30].index(admin_info["period_days"]) if admin_info["period_days"] in [10, 20, 30] else 2, format_func=lambda x: f"ہر {x} دن بعد")
            tot_mem = st.number_input("کل ممبران کی تعداد:", min_value=2, max_value=100, value=admin_info["total_members"], step=1)
            inst_amt = st.number_input("فی ممبر قسط (روپے):", min_value=100.0, value=admin_info["inst_amount"], step=500.0)
            d_mode = st.radio("کمیٹی کھولنے کا طریقہ:", ["یکمشت مکمل شیڈول (پہلے سے آخری نمبر تک)", "مرحلہ وار قرعہ اندازی (ہر باری پر ایک نام)"], index=0 if "یکمشت" in admin_info["draw_mode"] else 1)
            
            single_payout = tot_mem * inst_amt
            total_days = tot_mem * period_opt
            total_volume = single_payout * tot_mem
            
            st.success(f"""
            📊 **خودکار کمیٹی کیلکولیٹر (خلاصہ):**
            * 💰 **ایک ممبر کی نکلنے والی کمیٹی:** `{single_payout:,.0f} روپے`
            * ⏳ **مکمل کمیٹی کا کل دورانیہ:** `{total_days} دن` ({tot_mem} باریاں)
            * 🏦 **پوری کمیٹی کا مجموعی لین دین:** `{total_volume:,.0f} روپے`
            """)
            
            if st.form_submit_button("💾 سیٹنگز محفوظ کریں"):
                admins_ws.update_cell(admin_row_idx, 3, c_name.strip())
                admins_ws.update_cell(admin_row_idx, 4, c_city.strip())
                admins_ws.update_cell(admin_row_idx, 5, acc_title.strip())
                admins_ws.update_cell(admin_row_idx, 6, acc_num.strip())
                admins_ws.update_cell(admin_row_idx, 7, period_opt)
                admins_ws.update_cell(admin_row_idx, 8, tot_mem)
                admins_ws.update_cell(admin_row_idx, 9, inst_amt)
                admins_ws.update_cell(admin_row_idx, 10, d_mode)
                st.success("✅ کمیٹی کی تمام سیٹنگز محفوظ ہو گئیں!")
                st.rerun()
    # صفحہ 2: ممبران شامل کرنا
    elif st.session_state.c_page == "members":
        st.header("👥 کمیٹی ممبران کا اندراج")
        all_m_rows = mem_ws.get_all_values()
        my_mems = [r for r in all_m_rows[1:] if len(r) >= 6 and r[0].strip() == st.session_state.admin_id]
        
        st.write(f"رجسٹرڈ ممبران: **{len(my_mems)} / {admin_info['total_members']}**")
        with st.form("add_mem_form"):
            m_name = st.text_input("ممبر کا پورا نام:")
            m_phone = st.text_input("واٹس ایپ نمبر:")
            m_user = st.text_input("ممبر لاگ ان یوزر نیم (مثلاً ali12):").strip()
            m_pass = st.text_input("ممبر لاگ ان پاس ورڈ:").strip()
            if st.form_submit_button("➕ ممبر شامل کریں"):
                if m_name.strip() and m_user and m_pass:
                    if any(r[1].strip() == m_user for r in all_m_rows[1:] if len(r) >= 2):
                        st.error("یہ یوزر نیم پہلے سے موجود ہے، کوئی دوسرا رکھیں۔")
                    else:
                        mem_ws.append_row([st.session_state.admin_id, m_user, make_hash(m_pass), m_name.strip(), m_phone.strip(), "باقی ہے"])
                        st.success(f"ممبر '{m_name}' شامل ہو گیا! اس کا یوزر نیم `{m_user}` اور پاس ورڈ `{m_pass}` ہے۔")
                        st.rerun()
                else:
                    st.error("نام، یوزر نیم اور پاس ورڈ لازمی ہیں۔")

        if my_mems:
            st.divider()
            st.table([{"نام": r[3], "فون": r[4], "یوزر نیم": r[1], "کمیٹی اسٹیٹس": r[5]} for r in my_mems])

    # صفحہ 3: قسط وصولی و TID تصدیق
    elif st.session_state.c_page == "payments":
        st.header("💰 قسط وصولی و آن لائن تصدیق")
        all_m_rows = mem_ws.get_all_values()
        my_mems = [r for r in all_m_rows[1:] if len(r) >= 6 and r[0].strip() == st.session_state.admin_id]
        all_p_rows = pay_ws.get_all_values()
        
        t1, t2, t3 = st.tabs(["⏳ آن لائن TID تصدیق (Pending)", "💵 نقد (Cash) قسط جمع کریں", "📜 مکمل وصولی ریکارڈ"])
        
        with t1:
            pending_list = []
            for idx, r in enumerate(all_p_rows[1:], start=2):
                if len(r) >= 8 and r[0].strip() == st.session_state.admin_id and r[6].strip() == "Pending":
                    pending_list.append((idx, r))
            if not pending_list:
                st.info("کوئی آن لائن ادائیگی تصدیق کے لیے زیرِ التواء نہیں ہے۔")
            else:
                for p_idx, p_row in pending_list:
                    st.warning(f"👤 **{p_row[2]}** | باری: **{p_row[3]}** | رقم: **{p_row[4]} روپے** | تفصیل: `{p_row[5]}` ({p_row[7]})")
                    c_ok, c_no = st.columns(2)
                    if c_ok.button("✅ تصدیق کریں (Approve)", key=f"app_{p_idx}"):
                        pay_ws.update_cell(p_idx, 7, "Approved")
                        st.success("ادائیگی منظور ہو گئی!")
                        st.rerun()
                    if c_no.button("❌ مسترد کریں (Reject)", key=f"rej_{p_idx}"):
                        pay_ws.update_cell(p_idx, 7, "Rejected")
                        st.error("ادائیگی مسترد کر دی گئی۔")
                        st.rerun()

        with t2:
            if not my_mems:
                st.info("پہلے ممبران شامل کریں۔")
            else:
                with st.form("cash_pay_form"):
                    sel_mem_name = st.selectbox("ممبر منتخب کریں:", [r[3] for r in my_mems])
                    sel_mem_obj = next(r for r in my_mems if r[3] == sel_mem_name)
                    turn_lbl = st.text_input("باری / مہینہ لکھیں (مثلاً پہلی باری یا نومبر 2026):")
                    cash_amt = st.number_input("وصول شدہ نقد رقم:", value=admin_info["inst_amount"], step=500.0)
                    if st.form_submit_button("💾 نقد قسط محفوظ کریں"):
                        if turn_lbl.strip():
                            now_pk = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                            pay_ws.append_row([st.session_state.admin_id, sel_mem_obj[1], sel_mem_name, turn_lbl.strip(), cash_amt, "نقد (Cash)", "Approved", now_pk])
                            st.success(f"{sel_mem_name} کی نقد قسط محفوظ ہو گئی!")
                            st.rerun()
                        else:
                            st.error("باری یا مہینے کا نام لکھیں۔")

        with t3:
            my_pays = [r for r in all_p_rows[1:] if len(r) >= 8 and r[0].strip() == st.session_state.admin_id and r[6].strip() == "Approved"]
            if my_pays:
                tot_collected = sum(float(r[4]) for r in my_pays)
                st.metric("کل تصدیق شدہ جمع رقم", f"{tot_collected:,.0f} روپے")
                st.table([{"ممبر": r[2], "باری": r[3], "رقم": r[4], "ذریعہ": r[5], "وقت": r[7]} for r in my_pays])
            else:
                st.info("ابھی کوئی تصدیق شدہ قسط موجود نہیں۔")

    # صفحہ 4: کمیٹی کھولنا (قرعہ اندازی)
    elif st.session_state.c_page == "draw":
        st.header("🎲 کمیٹی کھولیں (خودکار قرعہ اندازی)")
        all_m_rows = mem_ws.get_all_values()
        my_mems = [(idx, r) for idx, r in enumerate(all_m_rows[1:], start=2) if len(r) >= 6 and r[0].strip() == st.session_state.admin_id]
        all_d_rows = draw_ws.get_all_values()
        my_draws = [r for r in all_d_rows[1:] if len(r) >= 5 and r[0].strip() == st.session_state.admin_id]

        st.info(f"منتخب کردہ طریقہ: **{admin_info['draw_mode']}**")

        if "یکمشت" in admin_info["draw_mode"]:
            if my_draws:
                st.success("✅ مکمل شیڈول پہلے ہی کھولا جا چکا ہے:")
                st.table([{"نمبر (باری)": f"نمبر {r[1]}", "ممبر کا نام": r[2], "تاریخ": r[4]} for r in my_draws])
            else:
                if len(my_mems) < 2:
                    st.warning("قرعہ اندازی کے لیے کم از کم 2 ممبران شامل کریں۔")
                else:
                    if st.button("🎰 تمام ممبران کی مکمل قرعہ اندازی ایک ساتھ کریں"):
                        shuffled = list(my_mems)
                        random.shuffle(shuffled)
                        now_pk = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                        for turn_no, (m_idx, m_row) in enumerate(shuffled, start=1):
                            draw_ws.append_row([st.session_state.admin_id, turn_no, m_row[3], m_row[1], now_pk])
                            mem_ws.update_cell(m_idx, 6, f"نمبر {turn_no}")
                        st.balloons()
                        st.success("🎉 مکمل کمیٹی شیڈول تیار ہو گیا ہے!")
                        st.rerun()
        else:
            remaining_mems = [(idx, r) for idx, r in my_mems if r[5].strip() == "باقی ہے"]
            st.write(f"باقی ماندہ ممبران جن کی کمیٹی ابھی نہیں نکلی: **{len(remaining_mems)}**")
            if remaining_mems:
                if st.button("🎲 اس باری کی کمیٹی کھولیں (1 نام نکالیں)"):
                    winner_idx, winner_row = random.choice(remaining_mems)
                    next_turn = len(my_draws) + 1
                    now_pk = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                    draw_ws.append_row([st.session_state.admin_id, next_turn, winner_row[3], winner_row[1], now_pk])
                    mem_ws.update_cell(winner_idx, 6, f"نکل گئی (نمبر {next_turn})")
                    st.balloons()
                    st.success(f"🎉 مبارک ہو! نمبر {next_turn} کی کمیٹی **{winner_row[3]}** کے نام نکلی ہے!")
                    st.rerun()
            else:
                st.success("تمام ممبران کی کمیٹیاں مکمل ہو چکی ہیں!")

            if my_draws:
                st.divider()
                st.subheader("🏆 اب تک نکلنے والی کمیٹیوں کی فہرست")
                st.table([{"باری": f"نمبر {r[1]}", "خوش نصیب ممبر": r[2], "تاریخ و وقت": r[4]} for r in my_draws])
# === 2. ممبر پورٹل (شفاف ڈیش بورڈ) ===
elif st.session_state.role == "member":
    st.title(f"🤝 {admin_info.get('committee_name', 'کمیٹی پورٹل')}")
    st.caption(f"خوش آمدید: **{st.session_state.display_name}** | علاقہ: {admin_info.get('city', '')}")

    single_payout = admin_info["total_members"] * admin_info["inst_amount"]
    st.info(f"""
    🏦 **کمیٹی ایڈمن اکاؤنٹ برائے ادائیگی (JazzCash / EasyPaisa):**
    * **اکاؤنٹ ٹائٹل:** `{admin_info['acc_title']}` | **نمبر:** `{admin_info['acc_number']}`
    * **فی قسط رقم:** `{admin_info['inst_amount']:,.0f} روپے` (ہر {admin_info['period_days']} دن بعد) | **نکلنے والی کمیٹی:** `{single_payout:,.0f} روپے`
    """)

    all_p_rows = pay_ws.get_all_values()
    all_d_rows = draw_ws.get_all_values()

    my_approved_pays = [r for r in all_p_rows[1:] if len(r) >= 8 and r[0].strip() == st.session_state.admin_id and r[1].strip() == st.session_state.user_id and r[6].strip() == "Approved"]
    total_admin_collected = sum(float(r[4]) for r in all_p_rows[1:] if len(r) >= 8 and r[0].strip() == st.session_state.admin_id and r[6].strip() == "Approved")
    my_paid_sum = sum(float(r[4]) for r in my_approved_pays)

    m1, m2 = st.columns(2)
    m1.metric("آپ کی جمع شدہ رقم", f"{my_paid_sum:,.0f} روپے")
    m2.metric("ایڈمن کے پاس کل جمع فنڈ", f"{total_admin_collected:,.0f} روپے")

    mtab1, mtab2, mtab3 = st.tabs(["🏆 قرعہ اندازی رزلٹ", "💳 قسط کی TID بھیجیں", "📜 میری قسطوں کا ریکارڈ"])

    with mtab1:
        my_draws = [r for r in all_d_rows[1:] if len(r) >= 5 and r[0].strip() == st.session_state.admin_id]
        if my_draws:
            st.table([{"باری": f"نمبر {r[1]}", "ممبر کا نام": r[2], "تاریخ و وقت": r[4]} for r in my_draws])
        else:
            st.info("ابھی ایڈمن کی طرف سے کمیٹی کی قرعہ اندازی نہیں کی گئی۔")

    with mtab2:
        st.write("ایڈمن کے اوپر دیے گئے نمبر پر رقم بھیجنے کے بعد ٹرانزیکشن آئی ڈی (TID) یہاں درج کریں:")
        with st.form("mem_send_tid_form"):
            m_turn = st.text_input("باری / مہینہ لکھیں (مثلاً پہلی باری):")
            m_amt = st.number_input("بھیجی گئی رقم:", value=admin_info["inst_amount"], step=500.0)
            m_tid = st.text_input("JazzCash / EasyPaisa ٹرانزیکشن آئی ڈی (TID):")
            if st.form_submit_button("📩 تصدیق کے لیے ایڈمن کو بھیجیں"):
                if m_turn.strip() and m_tid.strip():
                    now_pk = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                    pay_ws.append_row([st.session_state.admin_id, st.session_state.user_id, st.session_state.display_name, m_turn.strip(), m_amt, f"TID: {m_tid.strip()}", "Pending", now_pk])
                    st.success("✅ آپ کی TID ایڈمن کو بھیج دی گئی ہے! تصدیق ہوتے ہی آپ کے کھاتے میں شامل ہو جائے گی۔")
                else:
                    st.error("باری اور ٹرانزیکشن آئی ڈی دونوں لکھنا لازمی ہیں۔")

    with mtab3:
        my_all_pays = [r for r in all_p_rows[1:] if len(r) >= 8 and r[0].strip() == st.session_state.admin_id and r[1].strip() == st.session_state.user_id]
        if my_all_pays:
            st.table([{"باری": r[3], "رقم": r[4], "تفصیل": r[5], "اسٹیٹس": r[6], "وقت": r[7]} for r in my_all_pays])
        else:
            st.info("ابھی آپ کی کوئی قسط درج نہیں ہے۔")

    st.divider()
    _, ml_col = st.columns([3, 1])
    with ml_col:
        if st.button("🚪 لاگ آؤٹ", use_container_width=True):
            st.session_state.role = None
            st.rerun()
