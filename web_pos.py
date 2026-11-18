import streamlit as st
import gspread
import urllib.parse
import json
import os
import hashlib
from datetime import datetime, timezone, timedelta

PK_TIME = timezone(timedelta(hours=5))

st.set_page_config(page_title="POS & Business ERP System", page_icon="🛒", layout="centered")

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
    div[class*="StatusWidget"] {display: none !important;}
    a[href*="streamlit.io"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

def make_hash(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

@st.cache_resource
def get_spreadsheet():
    if os.path.exists("credentials.json"):
        client = gspread.service_account(filename="credentials.json")
        url = "https://docs.google.com/spreadsheets/d/1gHKID_B6t6A9WBP6WHaBt8QldJUUk76Urh8IWgIlThk/edit?gid=298455774#gid=298455774"
    else:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        client = gspread.service_account_from_dict(creds_dict)
        url = st.secrets["sheet_url"]
    return client.open_by_url(url)

try:
    sheet = get_spreadsheet()
except Exception as e:
    st.error(f"گوگل شیٹ سے رابطہ نہیں ہو سکا: {e}")
    st.stop()

if "visited" not in st.session_state:
    st.session_state.visited = True
    try:
        vis_ws = sheet.worksheet("Visitors")
        now_pk = datetime.now(PK_TIME)
        vis_ws.append_row([now_pk.strftime("%d-%m-%Y"), now_pk.strftime("%I:%M %p"), "🌐 Link Visit (لنک کھولا)"])
    except Exception:
        pass

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.shop_name = ""
    st.session_state.auto_deactivated_user = None

# --- 1. لاگ ان اسکرین ---
if not st.session_state.logged_in:
    st.title("🔐 اسمارٹ کاروبار و دکان مینجمنٹ سسٹم")
    st.caption("ورژن 6.6 | مکمل سیلز، اسٹاک، سپلائر کھاتہ و نفع نقصان")

    with st.form("login_form"):
        u_name = st.text_input("یوزر نیم (Username)").strip()
        u_pass = st.text_input("پاس ورڈ (Password)", type="password").strip()
        submit = st.form_submit_button("لاگ ان کریں")

        if submit:
            if u_name and u_pass:
                hashed_input = make_hash(u_pass)
                users_ws = sheet.worksheet("Users")
                all_rows = users_ws.get_all_values()
                user_found = False
                today_pk = datetime.now(PK_TIME)
                today_str = today_pk.strftime("%d-%m-%Y")

                for idx, row in enumerate(all_rows[1:], start=2):
                    if len(row) >= 4 and row[2].strip() == u_name and row[1].strip() == hashed_input:
                        user_found = True
                        current_status = row[3].strip().lower()
                        last_act_str = row[9].strip() if len(row) >= 10 else ""

                        # 3 دن غیر فعال ہونے کا خودکار چیک
                        is_expired = False
                        if current_status == "active" and last_act_str:
                            try:
                                last_dt = datetime.strptime(last_act_str, "%d-%m-%Y")
                                if (today_pk.date() - last_dt.date()).days > 3:
                                    is_expired = True
                            except Exception:
                                pass

                        if is_expired or current_status == "auto_inactive":
                            users_ws.update_cell(idx, 4, "auto_inactive")
                            st.session_state.auto_deactivated_user = {
                                "username": u_name,
                                "shop_name": row[0].strip(),
                                "owner": row[4].strip() if len(row) >= 5 else u_name,
                                "phone": row[5].strip() if len(row) >= 6 else ""
                            }
                            st.error("⏳ پالیسی کے تحت 3 دن تک استعمال نہ ہونے کی وجہ سے آپ کا اکاؤنٹ عارضی طور پر معطل (Auto-Inactive) ہو گیا ہے۔")
                        elif current_status == "active":
                            users_ws.update_cell(idx, 10, today_str)
                            st.session_state.logged_in = True
                            st.session_state.username = u_name
                            st.session_state.shop_name = row[0].strip()
                            st.session_state.auto_deactivated_user = None
                            st.rerun()
                        else:
                            st.error("آپ کا اکاؤنٹ فی الحال غیر فعال (Inactive / Pending) ہے۔ ایڈمن سے تصدیق کا انتظار کریں۔")
                        break

                if not user_found:
                    st.error("غلط یوزر نیم یا پاس ورڈ!")
            else:
                st.warning("براہ کرم یوزر نیم اور پاس ورڈ دونوں لکھیں۔")

    # صرف ان صارفین کے لیے بحالی کی درخواست کا بٹن جن کا اکاؤنٹ 3 دن کی وجہ سے بند ہوا ہو
    if st.session_state.auto_deactivated_user:
        deact = st.session_state.auto_deactivated_user
        st.warning(f"محترم **{deact['owner']}** ({deact['shop_name']})، اپنا اکاؤنٹ دوبارہ بحال کروانے کے لیے نیچے بٹن دبائیں:")
        if st.button("🔓 اکاؤنٹ دوبارہ فعال (Re-Activate) کرنے کی درخواست بھیجیں", use_container_width=True):
            try:
                fb_ws = sheet.worksheet("Feedback")
                now_str = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                fb_ws.append_row([
                    deact["username"],
                    deact["shop_name"],
                    f"🚨 [3-Day Auto-Inactive بحالی درخواست] مالک: {deact['owner']} | فون: {deact['phone']}",
                    now_str
                ])
                st.success("✅ آپ کی بحالی کی درخواست ایڈمن کو بھیج دی گئی ہے! جلد ہی آپ کا اکاؤنٹ دوبارہ فعال کر دیا جائے گا۔")
                st.session_state.auto_deactivated_user = None
            except Exception as e:
                st.error(f"درخواست بھیجنے میں مسئلہ آیا: {e}")

    st.divider()
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        with st.expander("🎬 ایپ کے فیچرز (ڈیمو)"):
            st.markdown("""
            * 🧾 **واٹس ایپ و پرنٹ بلنگ**
            * 📦 **خودکار اسٹاک و قیمتِ خرید**
            * 🚚 **سپلائر (ہول سیلر) کھاتہ**
            * 📒 **گاہکوں کا اسمارٹ ادھار لیجر**
            * 📈 **خالص نفع و نقصان رپورٹ**
            """)
    with col_info2:
        with st.expander("🆕 ورژن 6.6 میں نیا کیا ہے؟"):
            st.markdown("""
            * **سپلائر لین دین:** مال خریدنے پر خودکار اسٹاک انٹری اور سپلائر کا ادھار حساب۔
            * **نفع و نقصان رپورٹ:** خرید و فروخت کا موازنہ اور بقایا لین دین۔
            * **3 دن آٹو سیکیورٹی:** غیر فعال اکاؤنٹس کا خودکار تحفظ اور فوری بحالی بٹن۔
            """)

    st.markdown("### 🎬 ایپ انسٹال کرنے اور چلانے کا مکمل طریقہ (ویڈیو گائیڈ)")
    st.info("نئے دکاندار اکاؤنٹ بنانے سے پہلے یہ مختصر ویڈیو ضرور دیکھیں تاکہ آپ کو ایپ انسٹال کرنے اور بلنگ/کھاتہ چلانے کی مکمل سمجھ آ جائے:")

    if "show_demo_vid" not in st.session_state:
        st.session_state.show_demo_vid = False
    if "vid_logged" not in st.session_state:
        st.session_state.vid_logged = False

    if st.button("▶️ مکمل ڈیمو ویڈیو چلائیں (انسٹالیشن + فیچرز)", use_container_width=True):
        st.session_state.show_demo_vid = True
        if not st.session_state.vid_logged:
            st.session_state.vid_logged = True
            try:
                vis_ws = sheet.worksheet("Visitors")
                now_pk = datetime.now(PK_TIME)
                vis_ws.append_row([now_pk.strftime("%d-%m-%Y"), now_pk.strftime("%I:%M %p"), "🎬 Video Watched (ڈیمو ویڈیو دیکھی)"])
            except Exception:
                pass

    if st.session_state.show_demo_vid:
        if os.path.exists("final_master_hd.mp4"):
            st.video("final_master_hd.mp4")
        else:
            st.warning("ویڈیو فائل لوڈ ہو رہی ہے، براہ کرم یقین کر لیں کہ final_master_hd.mp4 GitHub پر اپ لوڈ ہو چکی ہے۔")

    st.divider()
    st.subheader("📝 نیا اکاؤنٹ بنوانے کے لیے درخواست دیں")
    st.info("""
    💳 **فیس ادائیگی کی تفصیلات (JazzCash / EasyPaisa):**
    * **اکاؤنٹ نمبر:** `0320-2609659` | **نام:** `Muhammad Younis` | **فیس:** `100 روپے`
    """)

    with st.form("new_account_request_form"):
        req_owner = st.text_input("آپ کا پورا نام (لازمی):")
        req_shop = st.text_input("دکان / کاروبار کا نام (لازمی):")
        req_phone = st.text_input("آپ کا واٹس ایپ نمبر (لازمی، مثلاً 03001234567):")
        req_trx = st.text_input("ٹرانزیکشن آئی ڈی (TID) لکھیں (اگر اسکرین شاٹ نہ ہو):")
        req_screenshot = st.file_uploader("یا 100 روپے فیس ادائیگی کا اسکرین شاٹ اپ لوڈ کریں:", type=["png", "jpg", "jpeg"])
        req_submit = st.form_submit_button("✅ لاگ ان کی درخواست جمع کروائیں")

        if req_submit:
            if req_owner[0].strip() and req_shop.strip() and req_phone.strip():
                if req_screenshot is not None or req_trx.strip():
                    try:
                        users_ws = sheet.worksheet("Users")
                        existing_users = users_ws.get_all_values()
                        next_num = len(existing_users) + 100
                        auto_username = f"dukan{next_num}"
                        now_pk = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                        today_only = datetime.now(PK_TIME).strftime("%d-%m-%Y")
                        tid_val = req_trx.strip() if req_trx.strip() else "نہیں لکھی"
                        ss_val = req_screenshot.name if req_screenshot is not None else "نہیں لگایا"

                        users_ws.append_row([
                            req_shop.strip(), "WAITING_PASS", auto_username, "pending",
                            req_owner[0].strip(), req_phone.strip(), tid_val, ss_val, now_pk, today_only
                        ])
                        try:
                            req_ws = sheet.worksheet("Requests")
                            req_ws.append_row([req_owner[0].strip(), req_shop.strip(), req_phone.strip(), tid_val, ss_val, now_pk])
                        except Exception:
                            pass

                        st.success("🎉 مبارک ہو! آپ کی درخواست موصول ہو گئی ہے۔ تصدیق کے بعد جلد ہی آپ کا اکاؤنٹ فعال کر کے واٹس ایپ پر اطلاع دی جائے گی۔")
                    except Exception as e:
                        st.error(f"درخواست محفوظ کرنے میں عارضی مسئلہ آیا: {e}")
                else:
                    st.warning("براہ کرم 100 روپے فیس کا اسکرین شاٹ اپ لوڈ کریں یا ٹرانزیکشن آئی ڈی (TID) لکھیں۔")
            else:
                st.error("براہ کرم اپنا نام، دکان کا نام اور واٹس ایپ نمبر لازمی درج کریں۔")
    st.stop()
current_user = st.session_state.username
shop_title = st.session_state.shop_name

st.title(f"🛒 {shop_title}")
st.caption(f"لاگ ان آئی ڈی: {current_user} | ورژن 6.6 (دکان و آڑھت ERP سسٹم)")

if "active_page" not in st.session_state:
    st.session_state.active_page = "home"

if st.session_state.active_page != "home":
    if st.button("🏠 مین ڈیش بورڈ پر واپس جائیں", key="back_home_btn", use_container_width=True):
        st.session_state.active_page = "home"
        st.rerun()
    st.divider()

stock_ws = sheet.worksheet("Stock")
khata_ws = sheet.worksheet("Khata")

all_stock_rows = stock_ws.get_all_values()
my_stock = []
for idx, row in enumerate(all_stock_rows[1:], start=2):
    if len(row) >= 4 and row[0].strip() == current_user:
        b_price = float(row[4]) if len(row) >= 5 and row[4].strip() else 0.0
        my_stock.append({
            "row_idx": idx,
            "item_name": row[1].strip(),
            "price": float(row[2]),
            "quantity": float(row[3]),
            "buy_price": b_price
        })

if st.session_state.active_page == "home":
    st.subheader("📌 مین ڈیش بورڈ — کام منتخب کریں:")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🧾\n\nکسٹمر بلنگ\n(مقررہ یا موقع کا ریٹ)", use_container_width=True):
            st.session_state.active_page = "billing"
            st.rerun()
        st.write("")
        if st.button("📒\n\nکسٹمر ادھار کھاتہ\n(لینی باقی رقم)", use_container_width=True):
            st.session_state.active_page = "khata"
            st.rerun()
        st.write("")
        if st.button("📈\n\nنفع و نقصان\nاور مکمل حساب کتاب", use_container_width=True):
            st.session_state.active_page = "pnl"
            st.rerun()

    with col_b:
        if st.button("🚚\n\nسپلائر خریداری بل\n(نقد + ادھار تقسیم)", use_container_width=True):
            st.session_state.active_page = "purchases"
            st.rerun()
        st.write("")
        if st.button("📦\n\nموجودہ اسٹاک\n(پرانا مال درج کریں)", use_container_width=True):
            st.session_state.active_page = "stock"
            st.rerun()
        st.write("")
        if st.button("🆕\n\nاپ ڈیٹ تفصیل (v6.2)\nو رائے (Feedback)", use_container_width=True):
            st.session_state.active_page = "updates_fb"
            st.rerun()

    st.divider()
    _, corner_col = st.columns(2)
    with corner_col:
        if st.button("🚪 لاگ آؤٹ", key="bottom_logout_btn", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.shop_name = ""
            st.session_state.cart = []
            st.session_state.active_page = "home"
            st.rerun()

elif st.session_state.active_page == "billing":
    st.header("🧾 نیا کسٹمر بل بنائیں")
    avail_stock = [i for i in my_stock if i["quantity"] > 0]
    if not avail_stock:
        st.warning("آپ کا اسٹاک خالی ہے! پہلے 'سپلائر خریداری بل' یا 'موجودہ اسٹاک' میں جا کر مال شامل کریں۔")
    else:
        if "cart" not in st.session_state:
            st.session_state.cart = []

        item_names = [item["item_name"] for item in avail_stock]
        selected_name = st.selectbox("چیز / جنس منتخب کریں:", item_names)
        selected_item = next(i for i in avail_stock if i["item_name"] == selected_name)

        rate_info = f"{selected_item['price']} روپے" if selected_item['price'] > 0 else "موقع پر طے ہوگا"
        st.info(f"📦 دستیاب اسٹاک: **{selected_item['quantity']}** | قیمتِ خرید: **{selected_item['buy_price']}** | مقررہ ریٹ: **{rate_info}**")

        sell_qty = st.number_input("تعداد / وزن درج کریں:", min_value=0.1, max_value=float(selected_item['quantity']), value=1.0, step=1.0)
        custom_sell_price = st.number_input("بیچنے کا ریٹ (موقع پر تبدیل بھی کر سکتے ہیں):", min_value=0.0, value=float(selected_item['price']), step=10.0)

        if st.button("➕ بل میں شامل کریں"):
            if custom_sell_price <= 0:
                st.error("براہ کرم بیچنے کا ریٹ (0 سے زیادہ) درج کریں!")
            elif selected_item['quantity'] >= sell_qty:
                total = custom_sell_price * sell_qty
                profit = (custom_sell_price - selected_item['buy_price']) * sell_qty if selected_item['buy_price'] > 0 else 0
                st.session_state.cart.append({
                    "name": selected_name,
                    "qty": sell_qty,
                    "price": custom_sell_price,
                    "total": total,
                    "profit": profit
                })
                new_qty = selected_item['quantity'] - sell_qty
                stock_ws.update_cell(selected_item['row_idx'], 4, new_qty)
                st.success(f"'{selected_name}' بل میں شامل ہو گیا!")
                st.rerun()
            else:
                st.error("اتنا اسٹاک موجود نہیں ہے!")

        if st.session_state.cart:
            st.divider()
            st.subheader("📄 تیار کردہ بل (Receipt)")
            current_dt = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
            bill_lines = [f"🏪 *{shop_title}*", f"📅 تاریخ و وقت: {current_dt}", "━━━━━━━━━━━━━━"]
            grand_total = 0
            html_rows = ""
            for item in st.session_state.cart:
                bill_lines.append(f"• {item['name']} ({item['qty']} x {item['price']}) = {item['total']} روپے")
                html_rows += f"<tr><td>{item['name']}</td><td>{item['qty']}</td><td>{item['price']}</td><td>{item['total']}</td></tr>"
                grand_total += item['total']
            bill_lines.append("━━━━━━━━━━━━━━")
            bill_lines.append(f"💰 *کل رقم: {grand_total} روپے*")
            bill_lines.append("شکریہ! دوبارہ تشریف لائیں۔")
            bill_text = "\n".join(bill_lines)

            st.code(bill_text, language="text")
            cust_phone = st.text_input("گاہک کا واٹس ایپ نمبر لکھیں (مثلاً 03001234567):", key="bill_phone")

            if cust_phone.strip():
                clean_phone = cust_phone.strip().replace("-", "").replace(" ", "")
                if clean_phone.startswith("03"):
                    clean_phone = "92" + clean_phone[1:]
                encoded_msg = urllib.parse.quote(bill_text)
                st.link_button("🟢 واٹس ایپ پر بل بھیجیں", f"https://wa.me{clean_phone}?text={encoded_msg}")
            else:
                encoded_msg = urllib.parse.quote(bill_text)
                st.link_button("🟢 واٹس ایپ کھولیں (فہرست سے گاہک چنیں)", f"https://wa.me?text={encoded_msg}")

            st.divider()
            st.subheader("💳 بل کی ادائیگی کی صورت منتخب کریں")
            bill_pay_mode = st.radio("ادائیگی کی قسم:", ["1️⃣ مکمل نقد بل (Full Cash)", "2️⃣ ادھار / جزوی نقد بل (کھاتے میں درج کریں)"], key="online_bill_mode")

            if "2️⃣" in bill_pay_mode:
                all_k_rows = khata_ws.get_all_values()
                my_k_list = []
                for k_idx, k_r in enumerate(all_k_rows[1:], start=2):
                    if len(k_r) >= 4 and k_r[0].strip() == current_user:
                        my_k_list.append({"row_idx": k_idx, "name": k_r[1].strip(), "phone": k_r[2].strip(), "balance": float(k_r[3])})

                cust_choice = st.radio("گاہک کی قسم:", ["پہلے سے رجسٹرڈ گاہک چنیں", "نیا گاہک درج کریں"], horizontal=True)
                sel_k_cust = None
                new_k_name = ""
                new_k_phone = ""

                if cust_choice == "پہلے سے رجسٹرڈ گاہک چنیں":
                    if my_k_list:
                        c_pick = st.selectbox("گاہک منتخب کریں:", [f"{x['name']} (بقایا: {x['balance']})" for x in my_k_list])
                        sel_k_cust = next(x for x in my_k_list if f"{x['name']} (بقایا: {x['balance']})" == c_pick)
                    else:
                        st.warning("ابھی کوئی پرانا گاہک رجسٹرڈ نہیں، اوپر 'نیا گاہک درج کریں' منتخب کریں۔")
                else:
                    new_k_name = st.text_input("نئے گاہک کا پورا نام (لازمی):")
                    new_k_phone = st.text_input("واٹس ایپ فون نمبر (مثلاً 03001234567):")

                cash_rec_now = st.number_input("اس بل میں سے کتنے نقد وصول ہوئے؟ (مکمل ادھار ہو تو 0 رہنے دیں):", min_value=0.0, max_value=float(grand_total), value=0.0, step=100.0)
                udhar_now = float(grand_total) - float(cash_rec_now)
                st.info(f"📊 **خلاصہ:** کل بل: `{grand_total}` | نقد وصول: `{cash_rec_now}` | **نیا ادھار: `{udhar_now}` روپے**")

                if st.button("💾 ادھار کھاتہ و مکمل اشیاء کی تفصیل محفوظ کریں"):
                    items_desc = ", ".join([f"{it['name']} ({it['qty']}x{it['price']})" for it in st.session_state.cart])
                    full_hist_note = f"بل اشیاء: {items_desc} | کل: {grand_total} | نقد: {cash_rec_now} | ادھار: {udhar_now}"
                    try:
                        hist_ws = sheet.worksheet("Khata_History")
                    except Exception:
                        hist_ws = None

                    if cust_choice == "پہلے سے رجسٹرڈ گاہک چنیں" and sel_k_cust:
                        updated_b = sel_k_cust['balance'] + udhar_now
                        khata_ws.update_cell(sel_k_cust['row_idx'], 4, updated_b)
                        if hist_ws:
                            hist_ws.append_row([current_user, sel_k_cust['name'], full_hist_note, udhar_now, current_dt])
                        st.success(f"✅ '{sel_k_cust['name']}' کے کھاتے میں {udhar_now} روپے ادھار مع اشیاء کی تفصیل محفوظ ہو گئے! کل بقایا: {updated_b} روپے")
                    elif cust_choice == "نیا گاہک درج کریں" and new_k_name.strip():
                        khata_ws.append_row([current_user, new_k_name.strip(), new_k_phone.strip(), udhar_now])
                        if hist_ws:
                            hist_ws.append_row([current_user, new_k_name.strip(), full_hist_note, udhar_now, current_dt])
                        st.success(f"✅ نیا گاہک '{new_k_name}' رجسٹر ہو گیا اور {udhar_now} روپے ادھار مع مکمل تفصیل درج ہو گئے!")
                    else:
                        st.error("براہ کرم گاہک منتخب کریں یا نئے گاہک کا نام لکھیں۔")

            if st.button("🔄 نیا بل شروع کریں (پرانا صاف کریں)"):
                st.session_state.cart = []
                st.rerun()
elif st.session_state.active_page == "purchases":
    st.header("🚚 سپلائر / زمیندار مجموعی خریداری بل")
    st.write("پہلے تمام خریدی گئی اشیاء فہرست میں ڈالیں، پھر نیچے کل بل میں سے نقد اور ادھار درج کریں:")

    try:
        pur_ws = sheet.worksheet("Purchases")
        sup_ws = sheet.worksheet("Suppliers")
    except Exception:
        st.error("گوگل شیٹ میں 'Purchases' اور 'Suppliers' ٹیبز موجود نہیں ہیں۔")
        st.stop()

    all_sup_rows = sup_ws.get_all_values()
    my_suppliers = []
    for idx, r in enumerate(all_sup_rows[1:], start=2):
        if len(r) >= 4 and r[0].strip() == current_user:
            my_suppliers.append({"row_idx": idx, "name": r[1].strip(), "phone": r[2].strip(), "payable": float(r[3])})

    if "pur_cart" not in st.session_state:
        st.session_state.pur_cart = []

    ptab1, ptab2, ptab3 = st.tabs(["📥 مجموعی خریداری بل بنائیں", "🏢 سپلائرز کا بقایا کھاتہ", "📜 خریداری ریکارڈ"])

    with ptab1:
        with st.form("add_pur_item_form"):
            p_item = st.text_input("چیز / جنس کا نام (لازمی):")
            p_qty = st.number_input("تعداد / وزن:", min_value=0.1, value=1.0, step=1.0)
            p_buy = st.number_input("فی یونٹ قیمتِ خرید (لازمی):", min_value=1.0, step=10.0)
            p_sell = st.number_input("فی یونٹ قیمتِ فروخت (اختیاری - آڑھت کے لیے 0 رہنے دیں):", min_value=0.0, value=0.0, step=10.0)
            if st.form_submit_button("➕ خریداری فہرست میں ڈالیں"):
                if p_item.strip():
                    st.session_state.pur_cart.append({
                        "item": p_item.strip(),
                        "qty": p_qty,
                        "buy": p_buy,
                        "sell": p_sell,
                        "total": p_qty * p_buy
                    })
                    st.success(f"'{p_item}' فہرست میں شامل ہو گیا!")
                    st.rerun()
                else:
                    st.error("چیز کا نام لکھیں۔")

        if st.session_state.pur_cart:
            st.divider()
            st.subheader("📋 زیرِ تیاری خریداری بل")
            st.table([{"چیز": x["item"], "مقدار": x["qty"], "ریٹ خرید": x["buy"], "کل": x["total"]} for x in st.session_state.pur_cart])
            grand_pur = sum(x["total"] for x in st.session_state.pur_cart)
            st.info(f"💰 **مجموعی خریداری بل: {grand_pur:,.0f} روپے**")

            with st.form("finalize_pur_form"):
                sup_name = st.text_input("سپلائر / زمیندار کا نام (لازمی):")
                sup_phone = st.text_input("سپلائر کا فون نمبر (اختیاری):")
                paid_cash = st.number_input("اس بل میں سے کتنے نقد ادا کیے؟ (باقی خودکار ادھار ہو جائے گا):", min_value=0.0, max_value=float(grand_pur), value=0.0, step=100.0)
                if st.form_submit_button("✅ بل مکمل کریں (اسٹاک و کھاتہ اپ ڈیٹ)"):
                    if sup_name.strip():
                        now_pk = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                        rem_debt = max(0.0, grand_pur - paid_cash)

                        for x in st.session_state.pur_cart:
                            ex = next((i for i in my_stock if i["item_name"].lower() == x["item"].lower()), None)
                            if ex:
                                new_q = ex["quantity"] + x["qty"]
                                new_s = x["sell"] if x["sell"] > 0 else ex["price"]
                                stock_ws.update_cell(ex["row_idx"], 3, new_s)
                                stock_ws.update_cell(ex["row_idx"], 4, new_q)
                                stock_ws.update_cell(ex["row_idx"], 5, x["buy"])
                            else:
                                stock_ws.append_row([current_user, x["item"], x["sell"], x["qty"], x["buy"]])

                            pur_ws.append_row([
                                current_user, sup_name.strip(), x["item"], x["qty"],
                                x["buy"], x["sell"], f"کل بل: {grand_pur} | نقد: {paid_cash}", now_pk
                            ])

                        if rem_debt > 0:
                            ex_sup = next((s for s in my_suppliers if s["name"].lower() == sup_name.strip().lower()), None)
                            if ex_sup:
                                sup_ws.update_cell(ex_sup["row_idx"], 4, ex_sup["payable"] + rem_debt)
                            else:
                                sup_ws.append_row([current_user, sup_name.strip(), sup_phone.strip(), rem_debt])

                        st.session_state.pur_cart = []
                        st.success(f"🎉 بل مکمل! نقد ادا: {paid_cash} روپے | سپلائر کے کھاتے میں ادھار: {rem_debt} روپے")
                        st.rerun()
                    else:
                        st.error("سپلائر کا نام لکھنا لازمی ہے۔")

            if st.button("❌ فہرست صاف کریں"):
                st.session_state.pur_cart = []
                st.rerun()

    with ptab2:
        if not my_suppliers:
            st.info("ابھی کوئی سپلائر درج نہیں ہے۔")
        else:
            tot_payable = sum(s["payable"] for s in my_suppliers)
            st.metric("سپلائرز کو کل دینی باقی رقم", f"{tot_payable:,.0f} روپے")
            st.table([{"سپلائر": s["name"], "فون": s["phone"], "دینی باقی": f"{s['payable']:,.0f} روپے"} for s in my_suppliers])

            with st.form("pay_sup_form"):
                sel_s_name = st.selectbox("سپلائر منتخب کریں:", [s["name"] for s in my_suppliers])
                sel_s = next(s for s in my_suppliers if s["name"] == sel_s_name)
                paid_to_s = st.number_input("ادا کی گئی رقم (روپے):", min_value=1.0, step=100.0)
                if st.form_submit_button("💾 ادائیگی منہا کریں"):
                    new_rem = max(0.0, sel_s["payable"] - paid_to_s)
                    sup_ws.update_cell(sel_s["row_idx"], 4, new_rem)
                    st.success(f"{sel_s_name} کا نیا بقایا {new_rem:,.0f} روپے رہ گیا ہے۔")
                    st.rerun()

    with ptab3:
        all_p_rows = pur_ws.get_all_values()
        my_p_list = [r for r in all_p_rows[1:] if len(r) >= 8 and r[0].strip() == current_user]
        if my_p_list:
            st.table([{"تاریخ": r[7], "سپلائر": r[1], "چیز": r[2], "مقدار": r[3], "خرید": r[4], "تفصیل": r[6]} for r in my_p_list])
        else:
            st.info("ابھی کوئی خریداری درج نہیں ہوئی۔")

elif st.session_state.active_page == "stock":
    st.header("📦 موجودہ اسٹاک (پہلے سے موجود مال درج کریں)")
    with st.form("direct_stock_form"):
        st_name = st.text_input("چیز / جنس کا نام (لازمی):")
        st_qty = st.number_input("موجودہ تعداد / وزن:", min_value=0.1, value=1.0, step=1.0)
        st_buy = st.number_input("فی یونٹ قیمتِ خرید (لازمی):", min_value=1.0, step=10.0)
        st_sell = st.number_input("فی یونٹ قیمتِ فروخت (اختیاری - آڑھت کے لیے 0 رہنے دیں):", min_value=0.0, value=0.0, step=10.0)
        if st.form_submit_button("💾 اسٹاک میں شامل کریں"):
            if st_name.strip():
                ex = next((i for i in my_stock if i["item_name"].lower() == st_name.strip().lower()), None)
                if ex:
                    stock_ws.update_cell(ex["row_idx"], 3, st_sell if st_sell > 0 else ex["price"])
                    stock_ws.update_cell(ex["row_idx"], 4, ex["quantity"] + st_qty)
                    stock_ws.update_cell(ex["row_idx"], 5, st_buy)
                else:
                    stock_ws.append_row([current_user, st_name.strip(), st_sell, st_qty, st_buy])
                st.success(f"'{st_name}' اسٹاک میں محفوظ ہو گیا!")
                st.rerun()
            else:
                st.error("چیز کا نام لکھیں۔")

    st.divider()
    if my_stock:
        st.table([
            {
                "چیز / جنس": i["item_name"],
                "قیمتِ خرید": i["buy_price"],
                "قیمتِ فروخت": i["price"] if i["price"] > 0 else "موقع پر طے",
                "بقایا مقدار": i["quantity"]
            }
            for i in my_stock
        ])
    else:
        st.info("ابھی کوئی اسٹاک درج نہیں ہے۔")
elif st.session_state.active_page == "pnl":
    st.header("📈 نفع و نقصان اور مکمل کاروباری حساب")
    all_k = khata_ws.get_all_values()
    cust_receivable = sum(float(r[3]) for r in all_k[1:] if len(r) >= 4 and r[0].strip() == current_user)

    try:
        sup_ws = sheet.worksheet("Suppliers")
        all_s = sup_ws.get_all_values()
        sup_payable = sum(float(r[3]) for r in all_s[1:] if len(r) >= 4 and r[0].strip() == current_user)
    except Exception:
        sup_payable = 0.0

    stock_cost_val = sum(i["buy_price"] * i["quantity"] for i in my_stock)
    stock_sell_val = sum((i["price"] if i["price"] > 0 else i["buy_price"]) * i["quantity"] for i in my_stock)
    expected_profit = sum((i["price"] - i["buy_price"]) * i["quantity"] for i in my_stock if i["price"] > 0 and i["buy_price"] > 0)

    c1, c2 = st.columns(2)
    c1.metric("💰 گاہکوں سے لینی باقی", f"{cust_receivable:,.0f} روپے")
    c2.metric("💸 سپلائرز کو دینی باقی", f"{sup_payable:,.0f} روپے")

    st.divider()
    c3, c4 = st.columns(2)
    c3.metric("📦 موجودہ اسٹاک مالیت (خرید)", f"{stock_cost_val:,.0f} روپے")
    c4.metric("✨ مقررہ اسٹاک پر متوقع منافع", f"{expected_profit:,.0f} روپے")

    st.divider()
    net_position = (cust_receivable + stock_sell_val) - sup_payable
    st.success(f"🏦 **مجموعی کاروباری پوزیشن:** `{net_position:,.0f} روپے`")

elif st.session_state.active_page == "khata":
    st.header("📒 کسٹمر ادھار کھاتہ سسٹم")
    all_khata_rows = khata_ws.get_all_values()
    my_khata = []
    for idx, row in enumerate(all_khata_rows[1:], start=2):
        if len(row) >= 4 and row[0].strip() == current_user:
            my_khata.append({"row_idx": idx, "customer_name": row[1].strip(), "phone": row[2].strip(), "balance": float(row[3])})

    try:
        hist_ws = sheet.worksheet("Khata_History")
        all_hist_rows = hist_ws.get_all_values()
    except Exception:
        hist_ws = None
        all_hist_rows = []

    tab1, tab2, tab3 = st.tabs(["🔄 ادھار / وصولی", "➕ نیا گاہک رجسٹر کریں", "📜 مکمل کھاتہ"])

    with tab1:
        if not my_khata:
            st.info("پہلے 'نیا گاہک رجسٹر کریں' میں جا کر گاہک کا نام شامل کریں۔")
        else:
            cust_names = [k["customer_name"] for k in my_khata]
            selected_c_name = st.selectbox("گاہک منتخب کریں:", cust_names)
            selected_cust = next(k for k in my_khata if k["customer_name"] == selected_c_name)
            st.info(f"👤 **{selected_cust['customer_name']}** | 📞 **{selected_cust['phone']}** | 💰 بقایا: **{selected_cust['balance']} روپے**")

            with st.form("existing_khata_form"):
                trans_type = st.radio("عمل منتخب کریں:", ["مزید ادھار دیں (+)", "رقم وصول کریں (-)"])
                trans_amount = st.number_input("رقم درج کریں (روپے):", min_value=1.0, step=100.0)
                if st.form_submit_button("💾 کھاتہ اپ ڈیٹ کریں"):
                    old_bal = selected_cust["balance"]
                    new_bal = old_bal + trans_amount if "دیں" in trans_type else max(0.0, old_bal - trans_amount)
                    log_type = "ادھار لیا (+)" if "دیں" in trans_type else "رقم جمع کروائی (-)"
                    khata_ws.update_cell(selected_cust["row_idx"], 4, new_bal)
                    if hist_ws:
                        now_dt = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                        hist_ws.append_row([current_user, selected_c_name, log_type, trans_amount, now_dt])
                    st.success(f"نیا بقایا {new_bal} روپے ہو گیا ہے۔")
                    st.rerun()

    with tab2:
        with st.form("new_cust_form"):
            new_c_name = st.text_input("نئے گاہک کا نام (لازمی):")
            new_c_phone = st.text_input("واٹس ایپ فون نمبر (لازمی):")
            first_udhar = st.number_input("ابتدائی ادھار رقم:", min_value=0.0, step=100.0)
            if st.form_submit_button("✅ نیا گاہک محفوظ کریں"):
                if new_c_name.strip() and new_c_phone.strip():
                    if any(k["customer_name"].lower() == new_c_name.strip().lower() for k in my_khata):
                        st.error("یہ نام پہلے سے موجود ہے!")
                    else:
                        khata_ws.append_row([current_user, new_c_name.strip(), new_c_phone.strip(), first_udhar])
                        if hist_ws and first_udhar > 0:
                            now_dt = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                            hist_ws.append_row([current_user, new_c_name.strip(), "ادھار لیا (+)", first_udhar, now_dt])
                        st.success("گاہک رجسٹر ہو گیا!")
                        st.rerun()
                else:
                    st.error("نام اور فون نمبر لازمی ہیں۔")

    with tab3:
        if not my_khata:
            st.info("ابھی کوئی گاہک رجسٹرڈ نہیں ہے۔")
        else:
            st.metric("مارکیٹ میں کل لینی باقی رقم", f"{sum(k['balance'] for k in my_khata):,.0f} روپے")
            st.divider()
            view_cust_name = st.selectbox("مکمل ہسٹری دیکھنے کے لیے گاہک منتخب کریں:", [k['customer_name'] for k in my_khata], key="view_ledger")
            v_cust = next(k for k in my_khata if k['customer_name'] == view_cust_name)

            cust_history = []
            for r in all_hist_rows[1:]:
                if len(r) >= 5 and r[0].strip() == current_user and r[1].strip() == view_cust_name:
                    cust_history.append({
                        "تاریخ و وقت": r[4],
                        "اشیاء و لین دین کی تفصیل": r[2],
                        "رقم (روپے)": r[3]
                    })

            st.info(f"👤 گاہک: **{v_cust['customer_name']}** | 📞 فون: **{v_cust['phone']}** | 💰 موجودہ بقایا: **{v_cust['balance']} روپے**")

            if cust_history:
                st.write("**📜 Khata_History سے مکمل ریکارڈ (تاریخ، وقت اور اشیاء):**")
                st.table(cust_history)
            else:
                st.warning("اس گاہک کی Khata_History شیٹ میں ابھی کوئی پرانی انٹری موجود نہیں ہے۔")

            clean_p = str(v_cust['phone']).strip().replace("-", "").replace(" ", "")
            if clean_p.startswith("03"):
                clean_p = "92" + clean_p[1:]
            ledger_msg = f"السلام علیکم {v_cust['customer_name']} صاحب، *{shop_title}* کے ذمہ آپ کا موجودہ بقایا ادھار *{v_cust['balance']} روپے* ہے۔ شکریہ!"
            st.link_button("📲 گاہک کو بقایا کھاتہ واٹس ایپ کریں", f"https://wa.me{clean_p}?text={urllib.parse.quote(ledger_msg)}")

elif st.session_state.active_page == "updates_fb":
    st.header("🆕 ورژن 6.6 اپ ڈیٹ لاگ و صارف کی رائے")
    st.info("""
    **اس نئے ورژن (v6.2) میں یہ جدید سہولیات شامل کی گئی ہیں:**
    1. **پہلے سے موجود اسٹاک کا اندراج:** اب آپ پرانا اسٹاک براہِ راست درج کر سکتے ہیں۔
    2. **سپلائر مجموعی بل (نقد + ادھار تقسیم):** اب پہلے متعدد اشیاء کا مجموعی بل بنتا ہے، اور پھر اس میں سے نقد رقم منہا ہو کر باقی خودکار طریقے سے سپلائر کے کھاتے میں درج ہو جاتی ہے۔
    3. **متغیر قیمتِ فروخت (آڑھت / منڈی سہولت):** اب مال خریدتے وقت قیمتِ فروخت خالی چھوڑی جا سکتی ہے اور کسٹمر بل بناتے وقت موقع کے ریٹ پر بل بنایا جا سکتا ہے۔
    """)
    st.divider()
    with st.form("feedback_form"):
        fb_msg = st.text_area("ان نئے فیچرز پر اپنی رائے یا تجویز لکھیں:")
        if st.form_submit_button("📩 ایڈمن کو پیغام بھیجیں"):
            if fb_msg.strip():
                try:
                    fb_ws = sheet.worksheet("Feedback")
                    now_str = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                    fb_ws.append_row([current_user, shop_title, fb_msg.strip(), now_str])
                    st.success("شکریہ! آپ کی رائے ایڈمن تک پہنچ گئی ہے۔")
                except Exception:
                    st.error("فیڈبیک بھیجنے میں مسئلہ آیا۔")
