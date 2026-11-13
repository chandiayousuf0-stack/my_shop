import streamlit as st
import gspread
import urllib.parse
import json
import os
import hashlib
from datetime import datetime

st.set_page_config(page_title="POS & Khata System", page_icon="🛒", layout="centered")

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
    st.subheader("📞 نیا اکاؤنٹ / لاگ ان بنوانے کے لیے رابطہ کریں")
    st.markdown("### 📱 **0320-2609659**")
    admin_wa = f"https://wa.me{urllib.parse.quote('السلام علیکم! مجھے اپنی دکان کے لیے POS سافٹ ویئر کا لاگ ان اکاؤنٹ بنوانا ہے۔')}"
    st.link_button("🟢 ایڈمن کو واٹس ایپ میسج کریں", admin_wa)
    st.stop()

current_user = st.session_state.username
shop_title = st.session_state.shop_name

st.title(f"🛒 {shop_title}")
st.caption(f"لاگ ان آئی ڈی: {current_user}")

menu = st.sidebar.radio(
    "مینیو منتخب کریں:",
    [
        "1. بلنگ اور سیلز (WhatsApp & Print)",
        "2. اسٹاک مینجمنٹ",
        "3. ادھار کھاتہ سسٹم",
        "4. رائے اور اپ ڈیٹ کی درخواست (Feedback)"
    ]
)

if st.sidebar.button("🚪 لاگ آؤٹ کریں"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.shop_name = ""
    st.session_state.cart = []
    st.rerun()

stock_ws = sheet.worksheet("Stock")
khata_ws = sheet.worksheet("Khata")

all_stock_rows = stock_ws.get_all_values()
my_stock = []
for idx, row in enumerate(all_stock_rows[1:], start=2):
    if len(row) >= 4 and row[0].strip() == current_user:
        my_stock.append({
            "row_idx": idx,
            "item_name": row[1],
            "price": float(row[2]),
            "quantity": int(float(row[3]))
        })
if menu == "1. بلنگ اور سیلز (WhatsApp & Print)":
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
            
            bill_lines = [f"🏪 *{shop_title}*", "━━━━━━━━━━━━━━"]
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
                printWin.document.write('<h2>{shop_title}</h2><hr>');
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
elif menu == "2. اسٹاک مینجمنٹ":
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

elif menu == "3. ادھار کھاتہ سسٹم":
    st.header("📒 ادھار کھاتہ (فون نمبر اور واٹس ایپ کے ساتھ)")
    
    all_khata_rows = khata_ws.get_all_values()
    my_khata = []
    for idx, row in enumerate(all_khata_rows[1:], start=2):
        if len(row) >= 4 and row[0].strip() == current_user:
            my_khata.append({
                "row_idx": idx,
                "customer_name": row[1],
                "phone": row[2],
                "balance": float(row[3])
            })

    tab1, tab2 = st.tabs(["➕ نیا ادھار / وصولی", "📋 کھاتہ لسٹ اور واٹس ایپ تقاضا"])
    
    with tab1:
        with st.form("khata_form"):
            c_name = st.text_input("گاہک کا نام (لازمی):")
            c_phone = st.text_input("گاہک کا واٹس ایپ نمبر (لازمی، مثلاً 03001234567):")
            action = st.radio("عمل منتخب کریں:", ["نیا ادھار ڈالیں (+)", "رقم وصول کریں (-)"])
            amount = st.number_input("رقم درج کریں (روپے):", min_value=1.0, step=100.0)
            khata_btn = st.form_submit_button("💾 کھاتہ محفوظ کریں")
            
            if khata_btn:
                if c_name.strip() and c_phone.strip():
                    existing_cust = next((k for k in my_khata if k["customer_name"].lower() == c_name.strip().lower()), None)
                    if existing_cust:
                        old_bal = existing_cust["balance"]
                        new_bal = (old_bal + amount) if action == "نیا ادھار ڈالیں (+)" else max(0.0, old_bal - amount)
                        khata_ws.update_cell(existing_cust["row_idx"], 3, c_phone.strip())
                        khata_ws.update_cell(existing_cust["row_idx"], 4, new_bal)
                        st.success(f"{c_name} کا کھاتہ اپ ڈیٹ ہو گیا! نیا بقایا: {new_bal} روپے")
                    else:
                        if action == "نیا ادھار ڈالیں (+)":
                            khata_ws.append_row([current_user, c_name.strip(), c_phone.strip(), amount])
                            st.success(f"نیا گاہک {c_name} ({amount} روپے ادھار) محفوظ ہو گیا!")
                        else:
                            st.error("یہ گاہک پہلے سے کھاتے میں موجود نہیں ہے۔")
                    st.rerun()
                else:
                    st.error("گاہک کا نام اور فون نمبر دونوں درج کرنا لازمی ہیں!")

    with tab2:
        if my_khata:
            total_udhar = sum(k["balance"] for k in my_khata)
            st.metric("مارکیٹ میں کل بقایا ادھار", f"{total_udhar} روپے")
            st.divider()
            
            for k in my_khata:
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**👤 {k['customer_name']}** | 📞 {k['phone']}")
                    st.write(f"بقایا رقم: **{k['balance']} روپے**")
                with col2:
                    if k['balance'] > 0:
                        clean_p = str(k['phone']).strip().replace("-", "").replace(" ", "")
                        if clean_p.startswith("03"):
                            clean_p = "92" + clean_p[1:]
                        reminder_msg = (
                            f"السلام علیکم {k['customer_name']} صاحب،\n"
                            f"*{shop_title}* کی طرف سے یاددہانی ہے کہ آپ کے ذمہ *{k['balance']} روپے* ادھار بقایا ہیں۔\n"
                            f"براہ کرم جلد ادائیگی کر دیں۔ شکریہ!"
                        )
                        wa_url = f"https://wa.me{clean_p}?text={urllib.parse.quote(reminder_msg)}"
                        st.link_button("📲 واٹس ایپ پر بل بھیجیں", wa_url)
                st.divider()
        else:
            st.info("ابھی کوئی ادھار کھاتہ موجود نہیں ہے۔")

elif menu == "4. رائے اور اپ ڈیٹ کی درخواست (Feedback)":
    st.header("💬 اپنی رائے یا نئی اپ ڈیٹ کی درخواست بھیجیں")
    st.write("اگر آپ چاہتے ہیں کہ اس سافٹ ویئر میں کوئی نیا فیچر شامل کیا جائے یا کوئی مسئلہ حل ہو، تو نیچے لکھ کر بھیجیں:")
    
    with st.form("feedback_form"):
        fb_msg = st.text_area("اپنا پیغام یا مشورہ یہاں لکھیں:")
        fb_btn = st.form_submit_button("📩 ایڈمن کو پیغام بھیجیں")
        
        if fb_btn:
            if fb_msg.strip():
                try:
                    fb_ws = sheet.worksheet("Feedback")
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    fb_ws.append_row([current_user, shop_title, fb_msg.strip(), now_str])
                    st.success("شکریہ! آپ کی رائے ایڈمن تک پہنچ گئی ہے، جلد ہی اس پر عمل کیا جائے گا۔")
                except Exception as e:
                    st.error("فیڈبیک بھیجنے میں مسئلہ آیا۔ یقین کر لیں کہ گوگل شیٹ میں 'Feedback' ٹیب موجود ہے۔")
            else:
                st.warning("براہ کرم خالی پیغام نہ بھیجیں۔")
