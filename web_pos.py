import streamlit as st
import gspread
import urllib.parse
import json
import os
import hashlib
from datetime import datetime, timezone, timedelta

PK_TIME = timezone(timedelta(hours=5))

st.set_page_config(page_title="POS & Smart Khata System", page_icon="🛒", layout="centered")

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

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.shop_name = ""

# --- 1. لاگ ان اسکرین ---
if not st.session_state.logged_in:
    st.title("🔐 دکان مینجمنٹ سسٹم - لاگ ان")
    st.info("صرف رجسٹرڈ دکاندار اپنا یوزر نیم اور پاس ورڈ درج کریں۔")

    with st.form("login_form"):
        u_name = st.text_input("یوزر نیم (Username)").strip()
        u_pass = st.text_input("پاس ورڈ (Password)", type="password").strip()
        submit = st.form_submit_button("لاگ ان کریں")

        if submit:
            if u_name and u_pass:
                hashed_input = make_hash(u_pass)
                users_ws = sheet.worksheet("Users")
                all_users = users_ws.get_all_records()
                user_found = False
                for row in all_users:
                    if str(row.get("username")).strip() == u_name and str(row.get("password")).strip() == hashed_input:
                        if str(row.get("status")).strip().lower() == "active":
                            st.session_state.logged_in = True
                            st.session_state.username = u_name
                            st.session_state.shop_name = row.get("shop_name", u_name)
                            user_found = True
                            st.rerun()
                        else:
                            st.error("آپ کا اکاؤنٹ فی الحال معطل (Inactive) ہے۔ ایڈمن سے رابطہ کریں۔")
                            user_found = True
                            break
                if not user_found:
                    st.error("غلط یوزر نیم یا پاس ورڈ!")
            else:
                st.warning("براہ کرم یوزر نیم اور پاس ورڈ دونوں لکھیں۔")

    st.divider()
    with st.expander("🎬 ایپ کے اندر کیا کچھ ہے؟ (ڈیمو اور فیچرز دیکھیں)"):
        st.markdown("""
        **لاگ ان کرنے کے بعد آپ کو یہ 4 پروفیشنل سہولیات ملیں گی:**
        * 🧾 **اسمارٹ بلنگ:** سامان منتخب کریں، بل خود بخود بنے گا، ایک کلک پر گاہک کو **واٹس ایپ** کریں یا صاف پرنٹ نکالیں۔
        * 📦 **اسٹاک کنٹرول:** ہر چیز کی قیمت اور بقایا تعداد محفوظ رکھیں۔ بل بنتے ہی اسٹاک خود کم ہو جائے گا۔
        * 📒 **ڈیجیٹل ادھار کھاتہ:** گاہک کا مکمل کھاتہ، کس تاریخ کو کتنا ادھار لیا اور کتنا جمع کروایا، اور ایک کلک پر واٹس ایپ پر تقاضا۔
        * 💬 **فوری اپ ڈیٹ سپورٹ:** ایپ کے اندر سے اپنی رائے بھیجیں اور اپنی دکان کی ضرورت کے مطابق نئے فیچرز شامل کروائیں۔
        """)

    st.subheader("📝 نیا اکاؤنٹ بنوانے کے لیے درخواست دیں")
    st.write("اپنی دکان کا ذاتی لاگ ان حاصل کرنے کے لیے **100 روپے** رجسٹریشن فیس ادا کریں اور نیچے فارم پُر کر کے جمع کروائیں:")

    st.info("""
    💳 **فیس ادائیگی کی تفصیلات (JazzCash / EasyPaisa):**
    * **اکاؤنٹ نمبر:** `0320-2609659`
    * **اکاؤنٹ کا نام (Title):** `Muhammad Younis`
    * **رجسٹریشن فیس:** صرف `100 روپے`
    """)

    with st.form("new_account_request_form"):
        req_owner = st.text_input("آپ کا پورا نام (لازمی):")
        req_shop = st.text_input("دکان / کاروبار کا نام (لازمی):")
        req_phone = st.text_input("آپ کا واٹس ایپ نمبر (لازمی، مثلاً 03001234567):")
        req_trx = st.text_input("ٹرانزیکشن آئی ڈی (TID) لکھیں (اگر اسکرین شاٹ نہ ہو):")
        req_screenshot = st.file_uploader("یا 100 روپے فیس ادائیگی کا اسکرین شاٹ اپ لوڈ کریں:", type=["png", "jpg", "jpeg"])
        req_submit = st.form_submit_button("✅ لاگ ان کی درخواست جمع کروائیں")

        if req_submit:
            if req_owner.strip() and req_shop.strip() and req_phone.strip():
                if req_screenshot is not None or req_trx.strip():
                    try:
                        users_ws = sheet.worksheet("Users")
                        existing_users = users_ws.get_all_values()
                        next_num = len(existing_users) + 100
                        auto_username = f"dukan{next_num}"
                        now_pk = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                        tid_val = req_trx.strip() if req_trx.strip() else "نہیں لکھی"
                        ss_val = req_screenshot.name if req_screenshot is not None else "نہیں لگایا"

                        users_ws.append_row([
                            req_shop.strip(),
                            "WAITING_PASS",
                            auto_username,
                            "pending",
                            req_owner.strip(),
                            req_phone.strip(),
                            tid_val,
                            ss_val,
                            now_pk
                        ])

                        try:
                            req_ws = sheet.worksheet("Requests")
                            req_ws.append_row([
                                req_owner.strip(),
                                req_shop.strip(),
                                req_phone.strip(),
                                tid_val,
                                ss_val,
                                now_pk
                            ])
                        except Exception:
                            pass

                        st.success("🎉 مبارک ہو! آپ کی درخواست اور 100 روپے فیس کی تفصیل موصول ہو گئی ہے۔ تصدیق کے بعد ان شاء اللہ جلد ہی آپ کا لاگ ان فعال کر کے آپ کے واٹس ایپ نمبر پر اطلاع دی جائے گی۔")
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
st.caption(f"لاگ ان آئی ڈی: {current_user} | ورژن 5.3 (مکمل آٹو رجسٹریشن و کلین ایپ)")

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
        my_stock.append({
            "row_idx": idx,
            "item_name": row[1].strip(),
            "price": float(row[2]),
            "quantity": int(float(row[3]))
        })

if st.session_state.active_page == "home":
    st.subheader("📌 مین ڈیش بورڈ — کام منتخب کریں:")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🧾\n\nبلنگ اور سیلز\n(WhatsApp & Print)", use_container_width=True):
            st.session_state.active_page = "billing"
            st.rerun()
        st.write("")
        if st.button("📒\n\nاسمارٹ ادھار کھاتہ\n(لیجر و تقاضا)", use_container_width=True):
            st.session_state.active_page = "khata"
            st.rerun()
    with col_b:
        if st.button("📦\n\nاسٹاک مینجمنٹ\n(سامان و قیمت)", use_container_width=True):
            st.session_state.active_page = "stock"
            st.rerun()
        st.write("")
        if st.button("💬\n\nرائے اور اپ ڈیٹ\n(Feedback)", use_container_width=True):
            st.session_state.active_page = "feedback"
            st.rerun()

    st.divider()
    _, corner_col = st.columns([2, 1])
    with corner_col:
        if st.button("🚪 لاگ آؤٹ", key="bottom_logout_btn", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.shop_name = ""
            st.session_state.cart = []
            st.session_state.active_page = "home"
            st.rerun()

elif st.session_state.active_page == "billing":
    st.header("🧾 نیا بل بنائیں")
    if not my_stock:
        st.warning("آپ کا اسٹاک خالی ہے! پہلے 'اسٹاک مینجمنٹ' میں جا کر سامان شامل کریں۔")
    else:
        if "cart" not in st.session_state:
            st.session_state.cart = []

        item_names = [item["item_name"] for item in my_stock]
        selected_name = st.selectbox("سامان منتخب کریں:", item_names)
        selected_item = next(i for i in my_stock if i["item_name"] == selected_name)

        st.write(f"فی یونٹ قیمت: **{selected_item['price']} روپے** | دستیاب اسٹاک: **{selected_item['quantity']}**")
        sell_qty = st.number_input("تعداد درج کریں:", min_value=1, max_value=max(1, selected_item['quantity']), step=1)

        if st.button("➕ بل میں شامل کریں"):
            if selected_item['quantity'] >= sell_qty:
                total = selected_item['price'] * sell_qty
                st.session_state.cart.append({
                    "name": selected_name,
                    "qty": sell_qty,
                    "price": selected_item['price'],
                    "total": total
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

            st.write("📋 **بل کاپی کرنے کے لیے باکس کے دائیں کونے پر کلک کریں:**")
            st.code(bill_text, language="text")

            st.write("📲 **گاہک کو واٹس ایپ پر بل بھیجیں:**")
            cust_phone = st.text_input("گاہک کا واٹس ایپ نمبر لکھیں (مثلاً 03001234567):", key="bill_phone")

            if cust_phone.strip():
                clean_phone = cust_phone.strip().replace("-", "").replace(" ", "")
                if clean_phone.startswith("03"):
                    clean_phone = "92" + clean_phone[1:]
                encoded_msg = urllib.parse.quote(bill_text)
                wa_link = f"https://wa.me{clean_phone}?text={encoded_msg}"
                st.link_button("🟢 واٹس ایپ پر بل بھیجیں", wa_link)
            else:
                encoded_msg = urllib.parse.quote(bill_text)
                st.link_button("🟢 واٹس ایپ کھولیں (فہرست سے گاہک چنیں)", f"https://wa.me?text={encoded_msg}")

            receipt_html = f"""
            <script>
            function printOnlyBill() {{
                var printWin = window.open('', '', 'width=400,height=600');
                printWin.document.write('<html><head><title>Print Bill</title>');
                printWin.document.write('<style>body{{font-family:sans-serif;text-align:center;direction:rtl;}} table{{width:100%;border-collapse:collapse;margin-top:10px;}} th,td{{border-bottom:1px dashed #000;padding:5px;text-align:right;}}</style>');
                printWin.document.write('</head><body>');
                printWin.document.write('<h2>{shop_title}</h2><p style="font-size:12px;">تاریخ و وقت: {current_dt}</p><hr>');
                printWin.document.write('<table><tr><th>چیز</th><th>تعداد</th><th>قیمت</th><th>کل</th></tr>{html_rows}</table>');
                printWin.document.write('<h3>کل رقم: {grand_total} روپے</h3><hr>');
                printWin.document.write('<p>شکریہ! دوبارہ تشریف لائیں۔</p>');
                printWin.document.write('</body></html>');
                printWin.document.close();
                printWin.focus();
                printWin.print();
                printWin.close();
            }}
            </script>
            <button onclick="printOnlyBill()" style="background-color:#2196F3;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-size:16px;margin-top:10px;">🖨️ صرف بل پرنٹ کریں (Clean Receipt)</button>
            """
            st.components.v1.html(receipt_html, height=65)

            if st.button("🔄 نیا بل شروع کریں (پرانا صاف کریں)"):
                st.session_state.cart = []
                st.rerun()
elif st.session_state.active_page == "stock":
    st.header("📦 اسٹاک مینجمنٹ")
    with st.form("add_stock_form"):
        new_item = st.text_input("نئی چیز کا نام:")
        new_price = st.number_input("فی یونٹ قیمت (روپے):", min_value=0.0, step=10.0)
        new_qty = st.number_input("مقدار (تعداد/بوری):", min_value=1, step=1)
        save_btn = st.form_submit_button("💾 اسٹاک میں محفوظ کریں")

        if save_btn:
            if new_item.strip():
                existing = next((i for i in my_stock if i["item_name"].lower() == new_item.strip().lower()), None)
                if existing:
                    updated_qty = existing["quantity"] + new_qty
                    stock_ws.update_cell(existing["row_idx"], 3, new_price)
                    stock_ws.update_cell(existing["row_idx"], 4, updated_qty)
                    st.success(f"'{new_item}' کا اسٹاک اور قیمت اپ ڈیٹ ہو گئی!")
                else:
                    stock_ws.append_row([current_user, new_item.strip(), new_price, new_qty])
                    st.success(f"'{new_item}' نیا اسٹاک شامل ہو گیا!")
                st.rerun()
            else:
                st.error("چیز کا نام لکھنا ضروری ہے۔")

    st.divider()
    st.subheader("موجودہ اسٹاک کی فہرست")
    if my_stock:
        display_stock = [{"پروڈکٹ": i["item_name"], "قیمت": i["price"], "بقایا مقدار": i["quantity"]} for i in my_stock]
        st.table(display_stock)
    else:
        st.info("ابھی کوئی اسٹاک درج نہیں ہے۔")

elif st.session_state.active_page == "khata":
    st.header("📒 اسمارٹ ادھار کھاتہ سسٹم")
    all_khata_rows = khata_ws.get_all_values()
    my_khata = []
    for idx, row in enumerate(all_khata_rows[1:], start=2):
        if len(row) >= 4 and row[0].strip() == current_user:
            my_khata.append({
                "row_idx": idx,
                "customer_name": row[1].strip(),
                "phone": row[2].strip(),
                "balance": float(row[3])
            })

    try:
        hist_ws = sheet.worksheet("Khata_History")
        all_hist_rows = hist_ws.get_all_values()
    except Exception:
        hist_ws = None
        all_hist_rows = []

    tab1, tab2, tab3 = st.tabs([
        "🔄 ادھار / وصولی (فہرست سے چنیں)",
        "➕ نیا گاہک رجسٹر کریں",
        "📜 گاہک کا مکمل کھاتہ اور بقایا"
    ])

    with tab1:
        if not my_khata:
            st.info("ابھی کوئی گاہک رجسٹرڈ نہیں ہے۔ پہلے 'نیا گاہک رجسٹر کریں' میں جا کر گاہک کا نام اور نمبر شامل کریں۔")
        else:
            st.subheader("پرانے گاہک کا لین دین درج کریں")
            cust_names = [k["customer_name"] for k in my_khata]
            selected_c_name = st.selectbox("گاہک منتخب کریں (کلک کریں):", cust_names)
            selected_cust = next(k for k in my_khata if k["customer_name"] == selected_c_name)

            st.info(f"👤 گاہک: **{selected_cust['customer_name']}** | 📞 فون: **{selected_cust['phone']}** | 💰 موجودہ بقایا: **{selected_cust['balance']} روپے**")

            with st.form("existing_khata_form"):
                trans_type = st.radio("عمل منتخب کریں:", ["مزید ادھار دیں (+)", "رقم وصول کریں (-)"])
                trans_amount = st.number_input("رقم درج کریں (روپے):", min_value=1.0, step=100.0)
                trans_btn = st.form_submit_button("💾 کھاتہ اپ ڈیٹ کریں")

                if trans_btn:
                    old_bal = selected_cust["balance"]
                    if trans_type == "مزید ادھار دیں (+)":
                        new_bal = old_bal + trans_amount
                        log_type = "ادھار لیا (+)"
                    else:
                        new_bal = max(0.0, old_bal - trans_amount)
                        log_type = "رقم جمع کروائی (-)"

                    khata_ws.update_cell(selected_cust["row_idx"], 4, new_bal)
                    if hist_ws:
                        now_dt = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                        hist_ws.append_row([current_user, selected_c_name, log_type, trans_amount, now_dt])
                    st.success(f"کامیابی! {selected_c_name} کا نیا بقایا {new_bal} روپے ہو گیا ہے۔")
                    st.rerun()
    with tab2:
        st.subheader("نئے گاہک کا کھاتہ کھولیں")
        with st.form("new_cust_form"):
            new_c_name = st.text_input("نئے گاہک کا نام (لازمی):")
            new_c_phone = st.text_input("واٹس ایپ فون نمبر (لازمی، مثلاً 03001234567):")
            first_udhar = st.number_input("ابتدائی ادھار رقم (اگر کوئی ہے):", min_value=0.0, step=100.0)
            add_cust_btn = st.form_submit_button("✅ نیا گاہک محفوظ کریں")

            if add_cust_btn:
                if new_c_name.strip() and new_c_phone.strip():
                    already_exists = any(k["customer_name"].lower() == new_c_name.strip().lower() for k in my_khata)
                    if already_exists:
                        st.error("یہ نام پہلے سے فہرست میں موجود ہے! پہلے ٹیب میں جا کر اس کا نام منتخب کریں۔")
                    else:
                        khata_ws.append_row([current_user, new_c_name.strip(), new_c_phone.strip(), first_udhar])
                        if hist_ws and first_udhar > 0:
                            now_dt = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                            hist_ws.append_row([current_user, new_c_name.strip(), "ادھار لیا (+)", first_udhar, now_dt])
                        st.success(f"گاہک '{new_c_name}' کامیابی سے رجسٹر ہو گیا!")
                        st.rerun()
                else:
                    st.error("گاہک کا نام اور فون نمبر دونوں درج کرنا لازمی ہیں۔")

    with tab3:
        if not my_khata:
            st.info("کوئی کھاتہ موجود نہیں ہے۔")
        else:
            total_market_udhar = sum(k["balance"] for k in my_khata)
            st.metric("مارکیٹ میں کل بقایا ادھار", f"{total_market_udhar} روپے")
            st.divider()

            view_cust_name = st.selectbox("تفصیلی کھاتہ دیکھنے کے لیے گاہک منتخب کریں:", [k["customer_name"] for k in my_khata], key="view_ledger")
            v_cust = next(k for k in my_khata if k["customer_name"] == view_cust_name)

            cust_history = []
            total_taken = 0.0
            total_paid = 0.0
            for r in all_hist_rows[1:]:
                if len(r) >= 5 and r[0].strip() == current_user and r[1].strip() == view_cust_name:
                    amt = float(r[3])
                    t_type = r[2].strip()
                    if "+" in t_type:
                        total_taken += amt
                    else:
                        total_paid += amt
                    cust_history.append({"تاریخ و وقت": r[4], "تفصیل": t_type, "رقم (روپے)": amt})

            c1, c2, c3 = st.columns(3)
            c1.metric("کل ادھار لیا", f"{total_taken} روپے")
            c2.metric("کل جمع کروایا", f"{total_paid} روپے")
            c3.metric("موجودہ بقایا", f"{v_cust['balance']} روپے")

            if cust_history:
                st.write("**📜 لین دین کی مکمل فہرست:**")
                st.table(cust_history)
            else:
                st.caption("ابھی اس گاہک کی پرانی تفصیل درج نہیں ہے۔")

            clean_p = str(v_cust['phone']).strip().replace("-", "").replace(" ", "")
            if clean_p.startswith("03"):
                clean_p = "92" + clean_p[1:]

            ledger_msg = (
                f"السلام علیکم {v_cust['customer_name']} صاحب،\n"
                f"*{shop_title}* کی طرف سے آپ کے کھاتے کی تفصیل:\n"
                f"• کل ادھار: {total_taken} روپے\n"
                f"• کل جمع شدہ: {total_paid} روپے\n"
                f"• *موجودہ بقایا رقم: {v_cust['balance']} روپے*\n"
                f"براہ کرم جلد ادائیگی کر دیں۔ شکریہ!"
            )
            wa_url = f"https://wa.me{clean_p}?text={urllib.parse.quote(ledger_msg)}"
            st.link_button("📲 گاہک کو مکمل کھاتہ واٹس ایپ کریں", wa_url)

elif st.session_state.active_page == "feedback":
    st.header("💬 اپنی رائے یا نئی اپ ڈیٹ کی درخواست بھیجیں")
    st.write("اگر آپ چاہتے ہیں کہ اس سافٹ ویئر میں کوئی نیا فیچر شامل کیا جائے یا کوئی مسئلہ حل ہو، تو نیچے لکھ کر بھیجیں:")

    with st.form("feedback_form"):
        fb_msg = st.text_area("اپنا پیغام یا مشورہ یہاں لکھیں:")
        fb_btn = st.form_submit_button("📩 ایڈمن کو پیغام بھیجیں")

        if fb_btn:
            if fb_msg.strip():
                try:
                    fb_ws = sheet.worksheet("Feedback")
                    now_str = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                    fb_ws.append_row([current_user, shop_title, fb_msg.strip(), now_str])
                    st.success("شکریہ! آپ کی رائے ایڈمن تک پہنچ گئی ہے، جلد ہی اس پر عمل کیا جائے گا۔")
                except Exception:
                    st.error("فیڈبیک بھیجنے میں مسئلہ آیا۔ یقین کر لیں کہ گوگل شیٹ میں Feedback ٹیب موجود ہے۔")
            else:
                st.warning("براہ کرم خالی پیغام نہ بھیجیں۔")
