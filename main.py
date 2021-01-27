import copy
import enum
import random
from abc import ABCMeta
from typing import Union, Optional, Dict


class Gender(enum.Enum):
    INVALID = enum.auto()
    MALE = enum.auto()
    FEMALE = enum.auto()


class Context:
    def __init__(self, gender: Gender = Gender.INVALID, tag: Optional[str] = None):
        self.gender = gender
        self.tag = tag
        self.subcontexts: Dict[str, Context] = {}

    def with_gender(self, gender: Gender):
        return Context(gender=gender, tag=self.tag)

    def with_tag(self, tag: str):
        return Context(gender=self.gender, tag=tag)

    def register_tagged_subcontext(self, context: 'Context'):
        assert context.tag
        self.subcontexts[context.tag] = context

    def get_subcontext(self, tag: str) -> 'Context':
        return self.subcontexts[tag]


class GenerateResult:
    def __init__(self, value: str, context: Context = None):
        self.value = value
        self.context = context


class BaseItem(metaclass=ABCMeta):
    def generate(self, context) -> GenerateResult:
        pass

    def def_tag(self, tag: str):
        return TagDefinitionWrapper(self, tag=tag)

    def apply_tag(self, tag: str):
        return TagApplicationWrapper(self, tag=tag)


def generate(item: Union[str, BaseItem], context: Context) -> GenerateResult:
    return item.generate(context) if isinstance(item, BaseItem) else GenerateResult(value=item, context=context)


class Options(BaseItem):
    def __init__(self, *args):
        self.list = list(map(lambda arg: Literal(arg) if isinstance(arg, str) else arg, args))

    def generate(self, context: Context):
        return generate(random.sample(self.list, 1)[0], context=context)


class Sequence(BaseItem):
    def __init__(self, *args):
        self.values = list(args)

    def generate(self, context: Context):
        context = copy.deepcopy(context)
        untagged_values = list(map(lambda item: self.generate_if_tag_def(item, context), self.values))

        return GenerateResult(''.join(map(lambda item: self.generate_untagged(item, context).value, untagged_values)))

    @staticmethod
    def generate_if_tag_def(item: BaseItem, context: Context) -> BaseItem:
        if not isinstance(item, TagDefinitionWrapper):
            return item

        item_result = item.generate(context)
        subcontext = item_result.context

        if subcontext and subcontext.tag:
            context.register_tagged_subcontext(subcontext)

        return Literal(item_result.value)

    @staticmethod
    def generate_untagged(item: BaseItem, context: Context) -> GenerateResult:
        if isinstance(item, TagApplicationWrapper):
            subcontext = context.get_subcontext(item.tag)
            assert subcontext, f'Subcontext {item.tag} not found'
            return generate(item, context=subcontext)
        else:
            return generate(item, context=context)


class Gendered(BaseItem):
    def __init__(self, male, female=None):
        self.male = male
        self.female = female or male + 'ה'

    def generate(self, context: Context):
        value = self.female if context.gender == Gender.FEMALE else self.male
        return GenerateResult(value=value, context=context)


class Literal(BaseItem):
    def __init__(self, value: str, gender: Gender = Gender.INVALID):
        self.value = value
        self.gender = gender

    @staticmethod
    def male(value: str):
        return Literal(value, gender=Gender.MALE)

    @staticmethod
    def female(value: str):
        return Literal(value, gender=Gender.FEMALE)

    def generate(self, context: Context):
        return GenerateResult(value=self.value, context=Context(gender=self.gender))


class TagDefinitionWrapper(BaseItem):
    def __init__(self, underlying_item: BaseItem, tag: str):
        self.underlying_item = underlying_item
        self.tag = tag

    def generate(self, context):
        generated_result = self.underlying_item.generate(context)
        context = generated_result.context.with_tag(self.tag)
        return GenerateResult(value=generated_result.value, context=context)


class TagApplicationWrapper(BaseItem):
    def __init__(self, underlying_item: BaseItem, tag: str):
        self.underlying_item = underlying_item
        self.tag = tag

    def generate(self, context):
        return self.underlying_item.generate(context)


someone = Options(Literal.male('סבא שלי'), Literal.female('סבתא שלי'), Literal.male('אבא שלי'), Literal.female('אמא שלי'), Literal.male('אחי'), Literal.female('אחותי'), Literal.male('גיסי'),
                  Literal.female('גיסתי'), Literal.male('חמי'), Literal.female('חמותי'), Literal.male('חבר שלי'), Literal.female('חברה שלי'), Literal.male('קולגה שלי'))
animal = Options('חתול', 'חתולה', 'כלב', 'כלבה', 'נחש', 'אוגר', 'חמוס', 'ארנב', 'ארנבת')
commodity = Sequence(Options('מים', 'שמן דקל', 'זרעי צ\'יה', 'פאנטה זירו', 'לחם מחמצת', 'לחם שעורים', 'ביצי חופש', 'גרעיני חמניה'), ' ',
                     Options('ללא גלוטן', 'בלי חומרים משמרים', 'לרגישים ללקטוז'))
dish = Sequence(Options('מרק', 'סלט', 'תבשיל', 'מאפה'), ' ',
                Options('עגבניות', 'מלפפונים', 'תרד', 'דיונונים', 'ארבע גבינות', 'שרימפס'), ' ',
                Options('הולנדי', 'גרמני', 'דני', 'צרפתי', 'איטלקי', 'תאילנדי', 'ישראלי', 'מקורי'))

arrangements = Options(
    Sequence('לשלם ', Options('חשבונות לפני ניתוק', 'חשבונות לפני הוצאה לפועל', 'מע"מ על רחפן שהוזמן מחו"ל', 'דו"ח בגין הפרת סגר', 'דמי חבר בהתאחדות התעשיינים', 'דמי שכירות בדיור מוגן')),
    Sequence('להעביר בעלות על ', Options('קורקינט חשמלי', 'וילה למסיבות רווקים', 'חדר בדירת שותפים', 'רכב אפס ק"מ')),
    Sequence('להחליף בטריות ל', Options('שלט לבית חכם', 'איי-רובוט', 'עמדת חיטוי נטענת', 'רובוט מטוס נינג\'גו', 'ויברטור', 'ערכת PCR ניידת', 'מטול שקופיות תומך זום')),
    Sequence('לקנות ', commodity, ' עבור ', dish),
)

blunt_object = Options(Literal.male('סקייטבורד'), Literal.female('אלת בייסבול'), Literal.female('מערכת סטריאו'), Literal.female('טלויזיה 75 אינץ\''),
                       Literal.female('פרגולה'), Literal.female('גיטרת בס'), Literal.female('מנורת לילה'), Literal.male('סדן'), Literal.male('שעון סבא'))

had_accident = Options(
    Sequence(Gendered('נפל'), ' מ', Options('גלשן רחיפה', 'סולם דו-שלבי', 'סולם ארבע-שלבי', 'מרפסת שמש', 'גג רעפים', 'מעקה בטיחות')),
    Sequence(Gendered('נפל').apply_tag('object'), ' ', Gendered(male='עליו', female='עליה'), ' ', blunt_object.def_tag('object')),
    Sequence(Options(Gendered('החליק'), Gendered('מעד')), ' על ', Options('גרם מדרגות לולייני', 'רצפת שיש', 'רצפת פרקט', 'קליפת בננה', 'צבע טרי', 'מזרון פילאטיס')),
)

accident_result = Options(
    Sequence(Options(Gendered('שבר'), Gendered('פצע'), Gendered('סדק')), ' את ', Options('המרפק', 'שורש כף היד', 'מפרק הכתף', 'עצם הבריח', 'עצם הזנב', 'מפרק הירך', 'רצפת האגן', 'כלוב הצלעות', 'המצח')),
    Sequence(Gendered('שכח'), ' את ', Options('הדרך הביתה', 'הסיסמה לג\'ימייל', 'הקוד בלובי', 'הסיסמה ל-WiFi', Gendered(male='שמו', female='שמה'), 'הסיסמה לקרן הפנסיה')),
    Sequence(Gendered('איבד'), ' את ', Options('המפתחות למשרד', 'המפתחות למקלט', 'האמון באנושות', 'החשק המיני', 'הדרכון', 'הרצון לחיות'))
)

something_happened = Sequence(had_accident, ' ', Options('וכתוצאה מכך ', 'ובעקבות זאת ', 'ו'), accident_result)

procedure = Sequence(
    Options('לעבור הליך רפואי', 'לעבור ניתוח', 'לקבל ייעוץ'), Options('', ' דחוף'), ' ל',
    Options('יישור', 'השחזת', 'השתלת', 'כריתת', 'הגדלת', 'הקטנת'), ' ',
    Options('חזה', 'גשר האף', 'נחיריים', 'גבות', 'שיניים טוחנות', 'שן בינה', 'עצמות לחיים', 'שערות באוזניים'), ' ',
    Options(Sequence('למען ', Options('אסתטיקה', 'השבחת הגזע', 'העצמה רוחנית', 'התנסות חווייתית', 'השקט הנפשי', 'שמחת החיים')),
            Sequence('בעקבות ', Options('התערבות עם חברים', 'נבואה תנ"כית', 'חלום בהקיץ', 'טיפול תרופתי', 'התבוננות עצמית', 'תקופת דכדוך', 'אימפוטנציה'))
            )
)

form = Options(
    Sequence('אני מביא ', Options(commodity, dish), ' ל', someone.def_tag('subject'), ' ש', something_happened.apply_tag('subject')),
    Sequence('אני מסיע את ', someone.def_tag('subject'), ' ', arrangements, ' ', Options('אחרי ש', 'כי '), something_happened.apply_tag('subject')),
    Sequence('אני ', Options(Sequence('מסיע את ', someone), Sequence('לוקח את ה', animal, ' של ', someone)), ' ', procedure),
)

random.seed(a=None, version=2)

for i in range(10):
    print(form.generate(Context()).value)
