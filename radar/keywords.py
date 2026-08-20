# -*- coding: utf-8 -*-
"""
Signal taxonomy for insurance-intent detection (Thai + English).

Everything the scorer knows lives here so it can be tuned without touching
logic.  Each entry is (weight, [patterns]).  Patterns are matched
case-insensitively as plain substrings against the post text; Thai has no
word boundaries so substring matching is the right primitive.
"""

# ---------------------------------------------------------------- intent ----
# Somebody actively shopping / asking for a recommendation. Highest value.
INTENT = [
    (30, [
        "อยากทำประกัน", "อยากซื้อประกัน", "กำลังหาประกัน", "กำลังมองหาประกัน",
        "มองหาประกัน", "หาประกันสุขภาพ", "หาประกันชีวิต", "สนใจทำประกัน",
        "อยากได้ประกัน", "จะทำประกัน", "คิดจะทำประกัน", "วางแผนทำประกัน",
        "looking for health insurance", "looking for life insurance",
        "want to buy insurance", "shopping for insurance",
        "need health insurance", "need life insurance",
    ]),
    (26, [
        "ประกันตัวไหนดี", "ประกันเจ้าไหนดี", "ประกันบริษัทไหนดี", "ประกันที่ไหนดี",
        "ประกันแบบไหนดี", "ประกันอันไหนดี", "ตัวไหนดีคะ", "ตัวไหนดีครับ",
        "เจ้าไหนดี", "ตัวไหนดี", "แบบไหนดี", "บริษัทไหนดี", "อันไหนดี", "ที่ไหนดี",
        "ค่ายไหน", "ยี่ห้อไหน", "ที่แนะนำ", "รีวิวจากคนใช้จริง",
        "which insurance", "best health insurance", "which health insurance",
        "insurance recommendation", "recommend insurance", "recommend a health",
    ]),
    (24, [
        "แนะนำประกัน", "รบกวนแนะนำประกัน", "ขอคำแนะนำประกัน", "ปรึกษาประกัน",
        "ขอคำปรึกษาประกัน", "รบกวนปรึกษา", "ช่วยแนะนำหน่อย", "ขอความเห็นหน่อย",
        "เลือกประกัน", "เปรียบเทียบประกัน", "ประกันเปรียบเทียบ",
        "insurance advice", "help me choose insurance", "compare insurance",
    ]),
    (20, [
        "ควรทำประกัน", "ควรซื้อประกัน", "จำเป็นต้องทำประกัน", "ทำประกันดีไหม",
        "ทำประกันดีมั้ย", "ประกันคุ้มไหม", "ควรมีประกัน",
        "should i get insurance", "is insurance worth", "do i need insurance",
    ]),
    (16, [
        "เบี้ยประกันเท่าไหร่", "เบี้ยเท่าไร", "เบี้ยแพงไหม", "ราคาประกัน",
        "ค่าเบี้ยประกัน", "ผ่อนเบี้ย", "งบประกัน", "งบเดือนละ",
        "insurance premium cost", "how much is insurance",
    ]),
    (14, [
        "ทำประกันที่ไหน", "ซื้อประกันที่ไหน", "สมัครประกัน", "ขอใบเสนอราคาประกัน",
        "ใบเสนอราคา", "อยากได้ตัวแทน", "หาตัวแทนประกัน", "หาที่ปรึกษาการเงิน",
        "where to buy insurance", "get a quote",
    ]),
]

# ------------------------------------------------------------ life events ---
# Trigger moments that create insurance need even without explicit shopping.
LIFE_EVENTS = [
    (18, [
        "ตั้งครรภ์", "ท้องอ่อน", "กำลังท้อง", "เพิ่งคลอด", "คลอดลูก", "มีลูก",
        "ลูกคนแรก", "เตรียมมีลูก", "ฝากครรภ์",
        "pregnant", "expecting a baby", "newborn", "having a baby",
    ]),
    (16, [
        "ตรวจเจอ", "หมอบอกว่า", "ตรวจพบก้อน", "ต้องผ่าตัด", "นอนโรงพยาบาล",
        "แอดมิท", "admit รพ", "ค่ารักษาแพง", "บิลค่ารักษา", "ค่าห้องแพง",
        "ป่วยหนัก", "เป็นมะเร็ง", "ตรวจสุขภาพเจอ",
        "hospital bill", "was diagnosed", "surgery next month",
    ]),
    (14, [
        "เพิ่งเริ่มทำงาน", "เด็กจบใหม่", "First jobber", "first jobber",
        "เพิ่งได้งาน", "ออกจากงาน", "ลาออกจากงาน", "ตกงาน", "ฟรีแลนซ์",
        "freelance ไม่มีประกัน", "ไม่มีประกันกลุ่ม", "ประกันกลุ่มหมด",
        "ประกันบริษัทไม่ครอบคลุม", "ลาออกแล้วประกันกลุ่ม",
        "just started working", "quit my job insurance", "no group insurance",
    ]),
    (14, [
        "แต่งงาน", "เพิ่งแต่งงาน", "ซื้อบ้าน", "ผ่อนบ้าน", "กู้บ้าน",
        "ซื้อรถ", "ออกรถใหม่", "ผ่อนรถ", "รถป้ายแดง",
        "got married", "bought a house", "new car",
    ]),
    (14, [
        "ลดหย่อนภาษี", "ยื่นภาษี", "ประหยัดภาษี", "วางแผนภาษี", "ภาษีสิ้นปี",
        "เกษียณ", "วางแผนเกษียณ", "บำนาญ", "เงินก้อนตอนแก่",
        "tax deduction", "retirement planning",
    ]),
    (12, [
        "ดูแลพ่อแม่", "พ่อแม่สูงอายุ", "ประกันให้พ่อแม่", "ประกันให้ลูก",
        "ประกันให้แฟน", "รับผิดชอบครอบครัว", "เสาหลักของบ้าน",
        "insurance for my parents", "insurance for my kids",
    ]),
    (12, [
        "ไปเที่ยวต่างประเทศ", "ขอวีซ่า", "วีซ่าเชงเก้น", "เรียนต่อต่างประเทศ",
        "ไปทำงานต่างประเทศ", "แลกเปลี่ยน",
        "schengen visa insurance", "travel insurance for",
    ]),
]

# ------------------------------------------------------------- products -----
# Also used to label the lead so you know what to pitch.
PRODUCTS = {
    "health": (10, [
        "ประกันสุขภาพ", "เหมาจ่าย", "ค่าห้อง", "ipd", "opd", "ค่ารักษาพยาบาล",
        "ประกันโรงพยาบาล", "health insurance", "medical insurance",
    ]),
    "critical_illness": (10, [
        "โรคร้ายแรง", "ประกันมะเร็ง", "ประกันโรคร้าย", "ci ประกัน",
        "critical illness", "cancer insurance",
    ]),
    "life": (10, [
        "ประกันชีวิต", "ตลอดชีพ", "สะสมทรัพย์", "ทุนประกัน", "คุ้มครองชีวิต",
        "life insurance", "term life", "whole life",
    ]),
    "motor": (10, [
        "ประกันรถ", "ประกันรถยนต์", "ประกันชั้น 1", "ประกันชั้น1", "ชั้น 2+",
        "พรบ รถ", "พ.ร.บ.", "ประกันมอเตอร์ไซค์", "car insurance",
    ]),
    "travel": (10, [
        "ประกันเดินทาง", "ประกันการเดินทาง", "travel insurance", "ประกันวีซ่า",
    ]),
    "accident_pa": (10, [
        "ประกันอุบัติเหตุ", "ประกัน pa", "personal accident",
    ]),
    "savings_annuity": (10, [
        "ประกันบำนาญ", "ประกันออมทรัพย์", "ยูนิตลิงค์", "unit linked",
        "unitlinked", "ประกันควบการลงทุน", "iwealthy",
    ]),
    "home_fire": (8, [
        "ประกันบ้าน", "ประกันอัคคีภัย", "ประกันคอนโด", "home insurance",
    ]),
}

# -------------------------------------------------------------- urgency -----
URGENCY = [
    (10, [
        "ด่วน", "เร่งด่วน", "ภายในสิ้นเดือน", "ก่อนสิ้นปี", "ภายในอาทิตย์นี้",
        "ต้องตัดสินใจ", "ตัดสินใจไม่ถูก", "ตัดสินใจวันนี้", "รีบ",
        "urgent", "asap", "by end of month", "need to decide",
    ]),
]

# ------------------------------------------------- switching / complaints ---
# Unhappy with a current policy = a real, if delicate, opportunity.
DISSATISFACTION = [
    (12, [
        "เคลมไม่ได้", "เคลมไม่ผ่าน", "ไม่จ่ายเคลม", "โดนปฏิเสธเคลม",
        "อยากยกเลิกกรมธรรม์", "เวนคืนกรมธรรม์", "อยากเปลี่ยนบริษัทประกัน",
        "ตัวแทนหาย", "ตัวแทนไม่ดูแล", "เบี้ยขึ้นเยอะ", "ปรับเบี้ย",
        "claim denied", "switch insurance company", "cancel my policy",
    ]),
]

# ------------------------------------------------------------- question -----
QUESTION_MARKERS = [
    "?", "ไหมคะ", "ไหมครับ", "มั้ยคะ", "มั้ยครับ", "หรือเปล่า", "ยังไงดี",
    "ยังไงคะ", "ยังไงครับ", "ยังไงดีคะ", "เริ่มต้นยังไง", "เริ่มยังไง",
    "ต้องทำยังไง", "ดีคะ", "ดีครับ", "ช่วยหน่อย", "รบกวน", "ขอคำแนะนำ",
    "สอบถาม", "หน่อยค่ะ", "หน่อยครับ", "อยากรู้ว่า",
    "any advice", "any recommendation", "help",
]

# ------------------------------------------------------------- negatives ----
# Agents advertising, corporate marketing, news, and listicle SEO spam.
# These are the difference between a lead list and a garbage list.
NEGATIVE = [
    (-45, [
        "สนใจทักแชท", "สนใจทักมา", "ทักแชทได้เลย", "inbox มาได้เลย",
        "สนใจ inbox", "ปรึกษาฟรีทักเลย", "ยินดีให้คำปรึกษาฟรี",
        "รับทำประกันทุกบริษัท", "รับสมัครตัวแทน", "สมัครตัวแทนประกัน",
        "หารายได้เสริม", "ตัวแทนประกันชีวิต ยินดี", "ทีมงานของเรา",
        "dm for details", "pm me for a quote", "contact me for insurance",
    ]),
    (-35, [
        "โปรโมชั่นพิเศษ", "โปรโมชั่นเดือนนี้", "ลดสูงสุด", "สมัครวันนี้รับ",
        "คลิกเลย", "ซื้อออนไลน์ที่นี่", "แคมเปญ", "ราคาพิเศษเฉพาะ",
        "เงื่อนไขเป็นไปตามที่บริษัทกำหนด", "รับส่วนลด",
        "buy now", "limited offer", "click here to apply",
    ]),
    (-40, [
        # Someone addressing an audience is publishing, not asking.
        "สำหรับใครที่", "ใครที่กำลังมองหา", "ใครที่ยังไม่มี", "ใครกำลังมองหา",
        "มาดูกันว่า", "วันนี้จะมาแนะนำ", "ขอแนะนำ", "แนะนำให้ทำ", "ขอแชร์ประสบการณ์",
        "สรุปให้แล้ว", "ครบจบในที่เดียว", "รู้ยัง", "บอกเลยว่า", "มาแล้ว!",
        "เปิดตัว", "ผลิตภัณฑ์ใหม่", "แบบประกันใหม่", "ตัวใหม่ล่าสุด",
        "thread ยาว", "เธรดนี้", "สาระ", "ความรู้การเงิน",
        "here's what you need to know", "a thread",
    ]),
    (-50, [
        # Wording that only appears on a policy brochure or ad creative.
        # Facebook results are often OCR'd from an image, and the images that
        # get posted are advertisements.
        "รับประกันโดย", "รับประกันภัยโดย", "เราพร้อมดูแลคุณ", "เชิญที่นี่",
        "คุ้มครองสูงสุด", "วงเงินสูงสุด", "สูงสุดปีละ", "สูงสุดครั้งละ",
        "ผู้ป่วยในครั้งละ", "เบิกค่าคลอดบุตรได้", "จ่ายเบี้ยเริ่มต้นเพียง",
        "เริ่มต้นเพียงวันละ", "บาท/วัน", "แผนความคุ้มครอง", "ตารางผลประโยชน์",
        "สนใจแผนนี้", "สอบถามรายละเอียดเพิ่มเติมได้ที่",
    ]),
    (-45, [
        # An agent retelling a client story, or opening with a rhetorical hook.
        # These read exactly like a real need until you notice who is talking.
        "ลูกค้าถามว่า", "ลูกค้าของผม", "ลูกค้าของเรา", "ลูกค้าท่านหนึ่ง",
        "เคสลูกค้า", "เคสนี้", "เมื่อวานลูกค้า", "มีลูกค้าทัก",
        "อยู่ใช่ไหม", "ใช่ไหมคะ? ถ้า", "ใช่ไหมครับ? ถ้า", "หรือเปล่า? ถ้าใช่",
        "ทักมาหาเรา", "ให้เราดูแล", "เราช่วยคุณได้", "ปรึกษาเราได้",
        "แอดมินยินดี", "แผนที่ใช่สำหรับคุณ", "ตัวแทนมืออาชีพ", "ทีมที่ปรึกษา",
        "รู้หรือไม่ว่า", "จากสถิติ", "เป็นตัวเลขที่", "ข้อมูลจากสมาคม",
    ]),
    (-40, [
        # Career / licensing questions about working in insurance.
        "สมัครงานประกัน", "ทำงานด้านประกัน", "อยากเป็นตัวแทน", "สอบใบอนุญาต",
        "สอบนายหน้า", "ใบอนุญาตตัวแทน", "เรียนต่อ ป.ตรี", "ควรเรียน",
        "เงินเดือนตัวแทน", "คอมมิชชั่นประกัน", "อยากทำงานบริษัทประกัน",
        "หางานประกัน", "สัมภาษณ์งาน",
    ]),
    (-30, [
        "รวม 10 ", "รวม 5 ", "top 10", "อันดับ 1 ประกัน", "จัดอันดับประกัน",
        "รีวิว 2568", "เปรียบเทียบ 10 แผน", "บทความนี้", "อ่านต่อที่",
        "สงวนลิขสิทธิ์", "บริษัทฯ ขอแจ้ง", "แถลงข่าว", "ผลประกอบการ",
        "กำไรสุทธิ", "เบี้ยรับรวม", "คปภ. เผย",
    ]),
]

# Domains that are almost always publishers/insurers, not people with a need.
# Social handles that broadcast finance/insurance content professionally.
# Their posts look like intent but never are.
BLOCKED_HANDLES = [
    "moneybuffalo", "aommoney", "finnomena", "gsbsociety", "krungsri",
    "kasikornbank", "scb_thailand", "ttbbank", "set_thailand", "wealthmagik",
    "moneyguru", "rabbitcare", "silkspan", "tqminsurance", "roojai",
    "aiathailand", "fwdthailand", "muangthailife", "prudentialth",
    "thairath", "khaosod", "matichon", "thestandardth", "brandinside",
    "longtungirl", "moneycoach", "insurancehub", "prakan",
]

BLOCKED_DOMAIN_PARTS = [
    "wikipedia.org", "youtube.com/channel", "shopee.co.th", "lazada.co.th",
    "prachachat.net", "thansettakij.com", "bangkokbiznews.com", "kaohoon.com",
    "moneyandbanking.co.th", "insurancethai.com", "tgia.org", "oic.or.th",
    "rabbitfinance", "priceza", "moneyduck", "silkspan", "roojai.com",
    "tqm.co.th", "724.co.th", "smk.co.th", "aia.co.th", "muangthai.co.th",
    "fwd.co.th", "prudential.co.th", "allianz.co.th", "tipinsure",
    "gettgo.com", "frank.co.th", "cigna.co.th", "krungthai-axa.co.th",
]
