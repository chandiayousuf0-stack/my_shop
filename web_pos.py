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
        vis_ws.append_row([now_pk.strftime("%d-%m-%Y"), now_pk.strftime("%I:%M %p")])
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
    st.caption("ورژن 6.0 | مکمل سیلز، اسٹاک، سپلائر کھاتہ و نفع نقصان")

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
        with st.expander("🆕 ورژن 6.0 میں نیا کیا ہے؟"):
            st.markdown("""
            * **سپلائر لین دین:** مال خریدنے پر خودکار اسٹاک انٹری اور سپلائر کا ادھار حساب۔
            * **نفع و نقصان رپورٹ:** خرید و فروخت کا موازنہ اور بقایا لین دین۔
            * **3 دن آٹو سیکیورٹی:** غیر فعال اکاؤنٹس کا خودکار تحفظ اور فوری بحالی بٹن۔
            """)

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
            if req_owner.strip() and req_shop.strip() and req_phone.strip():
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
                            req_owner.strip(), req_phone.strip(), tid_val, ss_val, now_pk, today_only
                        ])
                        try:
                            req_ws = sheet.worksheet("Requests")
                            req_ws.append_row([req_owner.strip(), req_shop.strip(), req_phone.strip(), tid_val, ss_val, now_pk])
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
st.caption(f"لاگ ان آئی ڈی: {current_user} | ورژن 6.0 (مکمل کاروباری ERP سسٹم)")

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
            "quantity": int(float(row[3])),
            "buy_price": b_price
        })

# === مین ڈیش بورڈ (6 پروفیشنل بٹن) ===
if st.session_state.active_page == "home":
    st.subheader("📌 مین ڈیش بورڈ — کام منتخب کریں:")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🧾\n\nبلنگ اور سیلز\n(کسٹمر بل)", use_container_width=True):
            st.session_state.active_page = "billing"
            st.rerun()
        st.write("")
        if st.button("📒\n\nکسٹمر ادھار کھاتہ\n(لینی باقی رقم)", use_container_width=True):
            st.session_state.active_page = "khata"
            st.rerun()
        st.write("")
        if st.button("🆕\n\nاپ ڈیٹ تفصیل (v6.0)\nو رائے (Feedback)", use_container_width=True):
            st.session_state.active_page = "updates_fb"
            st.rerun()

    with col_b:
        if st.button("🚚\n\nمال خریداری و سپلائر\n(خودکار اسٹاک انٹری)", use_container_width=True):
            st.session_state.active_page = "purchases"
            st.rerun()
        st.write("")
        if st.button("📦\n\nموجودہ اسٹاک\nو قیمتیں", use_container_width=True):
            st.session_state.active_page = "stock"
            st.rerun()
        st.write("")
        if st.button("📈\n\nنفع و نقصان\nاور مکمل حساب کتاب", use_container_width=True):
            st.session_state.active_page = "pnl"
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

# === صفحہ 1: بلنگ اور سیلز ===
elif st.session_state.active_page == "billing":
    st.header("🧾 نیا کسٹمر بل بنائیں")
    if not my_stock:
        st.warning("آپ کا اسٹاک خالی ہے! پہلے 'مال خریداری و سپلائر' یا 'موجودہ اسٹاک' میں جا کر سامان شامل کریں۔")
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
                profit = (selected_item['price'] - selected_item['buy_price']) * sell_qty if selected_item['buy_price'] > 0 else 0
                st.session_state.cart.append({
                    "name": selected_name,
                    "qty": sell_qty,
                    "price": selected_item['price'],
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
# === صفحہ 2: سپلائر سے مال خریداری و خودکار اسٹاک انٹری ===
elif st.session_state.active_page == "purchases":
    st.header("🚚 مال خریداری و سپلائر (Seller) کھاتہ")
    st.write("یہاں نئے آنے والے مال کی تفصیل درج کریں—ایپ خود بخود اسٹاک بڑھا دے گی اور سپلائر کا ادھار کھاتہ بھی محفوظ رکھے گی۔")

    try:
        pur_ws = sheet.worksheet("Purchases")
        sup_ws = sheet.worksheet("Suppliers")
    except Exception:
        st.error("گوگل شیٹ میں 'Purchases' اور 'Suppliers' ٹیبز موجود نہیں ہیں۔ براہ کرم پہلے یہ دونوں ٹیبز بنائیں۔")
        st.stop()

    all_sup_rows = sup_ws.get_all_values()
    my_suppliers = []
    for idx, r in enumerate(all_sup_rows[1:], start=2):
        if len(r) >= 4 and r[0].strip() == current_user:
            my_suppliers.append({
                "row_idx": idx,
                "name": r[1].strip(),
                "phone": r[2].strip(),
                "payable": float(r[3])
            })

    ptab1, ptab2, ptab3 = st.tabs(["📥 نیا مال خریدیں (اسٹاک انٹری)", "🏢 سپلائرز کا بقایا کھاتہ", "📜 خریداری کی مکمل تاریخ"])

    with ptab1:
        with st.form("purchase_entry_form"):
            sup_name = st.text_input("سپلائر / ہول سیلر کا نام (لازمی):")
            sup_phone = st.text_input("سپلائر کا فون نمبر (اختیاری):")
            p_item = st.text_input("خریدی گئی چیز کا نام (لازمی):")
            p_qty = st.number_input("تعداد / مقدار:", min_value=1, step=1)
            p_buy = st.number_input("فی یونٹ قیمتِ خرید (روپے):", min_value=1.0, step=10.0)
            p_sell = st.number_input("فی یونٹ قیمتِ فروخت (روپے):", min_value=1.0, step=10.0)
            pay_mode = st.radio("ادائیگی کی صورت:", ["نقد ادا کر دی (Paid)", "ادھار پر مال لیا (Credit - دینی باقی)"])

            if st.form_submit_button("✅ خریداری محفوظ کریں و اسٹاک بڑھائیں"):
                if sup_name.strip() and p_item.strip():
                    now_pk = datetime.now(PK_TIME).strftime("%d-%m-%Y %I:%M %p")
                    total_bill_cost = p_qty * p_buy

                    # 1. خودکار اسٹاک اپ ڈیٹ
                    existing = next((i for i in my_stock if i["item_name"].lower() == p_item.strip().lower()), None)
                    if existing:
                        new_q = existing["quantity"] + p_qty
                        stock_ws.update_cell(existing["row_idx"], 3, p_sell)
                        stock_ws.update_cell(existing["row_idx"], 4, new_q)
                        stock_ws.update_cell(existing["row_idx"], 5, p_buy)
                    else:
                        stock_ws.append_row([current_user, p_item.strip(), p_sell, p_qty, p_buy])

                    # 2. سپلائر کھاتہ اپ ڈیٹ (اگر ادھار پر لیا ہو)
                    ex_sup = next((s for s in my_suppliers if s["name"].lower() == sup_name.strip().lower()), None)
                    add_debt = total_bill_cost if "ادھار" in pay_mode else 0.0
                    if ex_sup:
                        sup_ws.update_cell(ex_sup["row_idx"], 4, ex_sup["payable"] + add_debt)
                    else:
                        sup_ws.append_row([current_user, sup_name.strip(), sup_phone.strip(), add_debt])

                    # 3. خریداری ریکارڈ میں اندراج
                    pur_ws.append_row([
                        current_user, sup_name.strip(), p_item.strip(),
                        p_qty, p_buy, p_sell, pay_mode, now_pk
                    ])
                    st.success(f"🎉 '{p_item}' کی {p_qty} تعداد خودکار طریقے سے اسٹاک میں شامل ہو گئی!")
                    st.rerun()
                else:
                    st.error("سپلائر کا نام اور چیز کا نام لازمی لکھیں۔")

    with ptab2:
        if not my_suppliers:
            st.info("ابھی کوئی سپلائر درج نہیں ہے۔")
        else:
            tot_payable = sum(s["payable"] for s in my_suppliers)
            st.metric("سپلائرز کو کل دینی باقی رقم", f"{tot_payable:,.0f} روپے")
            st.table([{"سپلائر کا نام": s["name"], "فون": s["phone"], "دینی باقی رقم": f"{s['payable']:,.0f} روپے"} for s in my_suppliers])

            st.subheader("💸 سپلائر کو ادائیگی درج کریں")
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
            st.table([
                {"تاریخ": r[7], "سپلائر": r[1], "چیز": r[2], "مقدار": r[3], "خرید": r[4], "فروخت": r[5], "حالت": r[6]}
                for r in my_p_list
            ])
        else:
            st.info("ابھی کوئی خریداری درج نہیں ہوئی۔")

# === صفحہ 3: موجودہ اسٹاک ===
elif st.session_state.active_page == "stock":
    st.header("📦 موجودہ اسٹاک و قیمتیں")
    if my_stock:
        display_stock = [
            {
                "پروڈکٹ": i["item_name"],
                "قیمتِ خرید": i["buy_price"],
                "قیمتِ فروخت": i["price"],
                "متوقع منافع/یونٹ": i["price"] - i["buy_price"] if i["buy_price"] > 0 else 0,
                "بقایا مقدار": i["quantity"]
            }
            for i in my_stock
        ]
        st.table(display_stock)
    else:
        st.info("ابھی کوئی اسٹاک درج نہیں ہے۔ 'مال خریداری و سپلائر' میں جا کر نیا اسٹاک درج کریں۔")

# === صفحہ 4: نفع و نقصان اور مکمل کاروباری خلاصہ ===
elif st.session_state.active_page == "pnl":
    st.header("📈 نفع و نقصان اور مکمل کاروباری حساب")

    # 1. کسٹمرز سے لینی باقی رقم
    all_k = khata_ws.get_all_values()
    cust_receivable = sum(float(r[3]) for r in all_k[1:] if len(r) >= 4 and r[0].strip() == current_user)

    # 2. سپلائرز کو دینی باقی رقم
    try:
        sup_ws = sheet.worksheet("Suppliers")
        all_s = sup_ws.get_all_values()
        sup_payable = sum(float(r[3]) for r in all_s[1:] if len(r) >= 4 and r[0].strip() == current_user)
    except Exception:
        sup_payable = 0.0

    # 3. موجودہ اسٹاک کی مالیت اور متوقع منافع
    stock_cost_val = sum(i["buy_price"] * i["quantity"] for i in my_stock)
    stock_sell_val = sum(i["price"] * i["quantity"] for i in my_stock)
    expected_profit = sum((i["price"] - i["buy_price"]) * i["quantity"] for i in my_stock if i["buy_price"] > 0)

    c1, c2 = st.columns(2)
    c1.metric("💰 گاہکوں سے لینی باقی (Receivable)", f"{cust_receivable:,.0f} روپے")
    c2.metric("💸 سپلائرز کو دینی باقی (Payable)", f"{sup_payable:,.0f} روپے")

    st.divider()
    c3, c4 = st.columns(2)
    c3.metric("📦 موجودہ اسٹاک کی کل مالیت (خرید)", f"{stock_cost_val:,.0f} روپے")
    c4.metric("✨ موجودہ اسٹاک پر متوقع منافع", f"{expected_profit:,.0f} روپے")

    st.divider()
    net_position = (cust_receivable + stock_sell_val) - sup_payable
    st.success(f"🏦 **مجموعی کاروباری پوزیشن (اسٹاک + وصولی منفی ادائیگی):** `{net_position:,.0f} روپے`")
# === صفحہ 5: کسٹمر ادھار کھاتہ ===
elif st.session_state.active_page == "khata":
    st.header("📒 کسٹمر ادھار کھاتہ سسٹم")
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
            cust_names = [k["customer_name"] for k in my_khata]
            selected_c_name = st.selectbox("گاہک منتخب کریں (کلک کریں):", cust_names)
            selected_cust = next(k for k in my_khata if k["customer_name"] == selected_c_name)

            st.info(f"👤 گاہک: **{selected_cust['customer_name']}** | 📞 فون: **{selected_cust['phone']}** | 💰 موجودہ بقایا: **{selected_cust['balance']} روپے**")

            with st.form("existing_khata_form"):
                trans_type = st.radio("عمل منتخب کریں:", ["مزید ادھار دیں (+)", "رقم وصول کریں (-)"])
                trans_amount = st.number_input("رقم درج کریں (روپے):", min_value=1.0, step=100.0)
                if st.form_submit_button("💾 کھاتہ اپ ڈیٹ کریں"):
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
        with st.form("new_cust_form"):
            new_c_name = st.text_input("نئے گاہک کا نام (لازمی):")
            new_c_phone = st.text_input("واٹس ایپ فون نمبر (لازمی، مثلاً 03001234567):")
            first_udhar = st.number_input("ابتدائی ادھار رقم (اگر کوئی ہے):", min_value=0.0, step=100.0)
            if st.form_submit_button("✅ نیا گاہک محفوظ کریں"):
                if new_c_name.strip() and new_c_phone.strip():
                    if any(k["customer_name"].lower() == new_c_name.strip().lower() for k in my_khata):
                        st.error("یہ نام پہلے سے فہرست میں موجود ہے!")
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
            st.metric("گاہکوں سے کل لینی باقی رقم", f"{total_market_udhar:,.0f} روپے")
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
            c1.metric("کل ادھار لیا", f"{total_taken:,.0f} روپے")
            c2.metric("کل جمع کروایا", f"{total_paid:,.0f} روپے")
            c3.metric("موجودہ بقایا", f"{v_cust['balance']:,.0f} روپے")

            if cust_history:
                st.table(cust_history)

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
            st.link_button("📲 گاہک کو مکمل کھاتہ واٹس ایپ کریں", f"https://wa.me{clean_p}?text={urllib.parse.quote(ledger_msg)}")

# === صفحہ 6: اپ ڈیٹ لاگ (v6.0) و فیڈبیک ===
elif st.session_state.active_page == "updates_fb":
    st.header("🆕 ورژن 6.0 اپ ڈیٹ لاگ و صارف کی رائے")
    st.info("""
    **اس نئے ورژن (v6.0) میں یہ پروفیشنل سہولیات شامل کی گئی ہیں:**
    1. **سپلائر (Seller) و خریداری کھاتہ:** اب آپ جس ہول سیلر سے مال خریدیں گے اس کا ریکارڈ اور ادھار کھاتہ الگ محفوظ ہوگا، اور سامان خودکار طریقے سے اسٹاک میں شامل ہو جائے گا۔
    2. **نفع و نقصان (Profit & Loss) رپورٹ:** اب آپ ایک کلک پر دیکھ سکتے ہیں کہ کس چیز کی قیمتِ خرید و فروخت کیا ہے، گاہکوں سے کل کتنی رقم لینی ہے اور سپلائرز کو کتنی دینی ہے۔
    3. **3 دن اکاؤنٹ سیکیورٹی پالیسی:** 3 دن تک غیر فعال رہنے والا اکاؤنٹ عارضی معطل ہو جاتا ہے اور صرف اسی صارف کو فوری بحالی کا بٹن دکھائی دیتا ہے۔
    """)

    st.divider()
    st.subheader("💬 ان نئے فیچرز پر اپنی رائے یا مزید تجویز بھیجیں")
    with st.form("feedback_form"):
        fb_msg = st.text_area("اپنا پیغام یا مشورہ یہاں لکھیں:")
        if st.form_submit_button("📩 ایڈمن کو پیغام بھیجیں"):
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
