## أهداف المشروع
- تعلم أساسيات الذكاء الاصطناعي وتطبيقاته.
- بناء مساعد شخصي ذكي خطوة بخطوة.
- تطوير مهاراتي في البرمجة.

## خطة التعلم
1. إتقان لغة بايثون.
2. فهم أساسيات تعلم الآلة (Machine Learning).
3. التعرف على نماذج اللغة الكبيرة (LLMs).

## المصادر
- (سأضع هنا روابط للدروس والكتب التي سأتابعها لاحقاً)

## تشخيص فشل التشغيل في GitHub Actions

إذا كانت المهمة تتوقف عند `urllib.request.urlopen(...)` أثناء إرسال رسالة إلى
Telegram، فهذه ليست مشكلة في بايثون نفسه؛ بل إن واجهة Telegram أعادت استجابة
HTTP غير ناجحة ولم يعرض السجل رمز الحالة أو نص الاستجابة. لا يمكن الجزم من
المقتطف المرفق وحده هل هي `401` أو `400`، لأن السطر الأخير من الاستثناء محذوف.

### المعلومات التي يجب إضافتها إلى السجل

عند التعامل مع `HTTPError`، اطبع رمز الحالة ونص الاستجابة (من دون طباعة
التوكن) قبل إنهاء البرنامج. مثال آمن يمكن وضعه حول طلب Telegram:

```python
import urllib.request
from urllib.error import HTTPError, URLError

try:
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()
except HTTPError as error:
    details = error.read().decode("utf-8", errors="replace")
    raise RuntimeError(
        f"Telegram API request failed (HTTP {error.code}): {details}"
    ) from error
except URLError as error:
    raise RuntimeError(f"Unable to reach Telegram API: {error.reason}") from error
```

### خطوات الإصلاح حسب رمز الاستجابة

1. **`401 Unauthorized`**: أعد إنشاء التوكن من `@BotFather`، ثم حدّث سرّ
   GitHub Actions الذي يمرَّر إلى `TELEGRAM_BOT_TOKEN`. تحقق من عدم وجود مسافات
   أو علامات اقتباس حول القيمة.
2. **`400 Bad Request: chat not found`**: أرسل `/start` إلى البوت من الحساب أو
   المجموعة المستهدفة، وتأكد من أن `TELEGRAM_CHAT_ID` صحيح. في المجموعات قد يكون
   المعرّف سالباً ويبدأ غالباً بـ `-100`.
3. **`403 Forbidden`**: لا يستطيع البوت مراسلة المحادثة؛ ألغِ حظره أو أضِفه إلى
   المجموعة ومنحه صلاحية الإرسال.
4. **`429 Too Many Requests`**: طبّق انتظاراً وإعادة محاولة باستخدام قيمة
   `retry_after` التي تعيدها Telegram، بدلاً من إعادة الإرسال فوراً.

بعد تعديل الأسرار، شغّل workflow مرة أخرى ولا تطبع قيمة التوكن في السجل أو في
رسالة الخطأ.
