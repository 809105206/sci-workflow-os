from __future__ import annotations

from typing import TypedDict


class ChineseLiteratureSource(TypedDict):
    key: str
    name: str
    coverage: str
    access: str
    search_url: str
    machine_access: str
    import_path: str
    role: str


_CHINESE_LITERATURE_SOURCES: tuple[ChineseLiteratureSource, ...] = (
    {
        "key": "openalex",
        "name": "OpenAlex（中文过滤）",
        "coverage": "跨学科中文与国际学术题录、引文和开放获取状态",
        "access": "开放 API；免费 key 有每日额度",
        "search_url": "https://openalex.org/works",
        "machine_access": "sciops literature search-cn / SCI Workflow OS MCP",
        "import_path": "直接生成标准 CSV；引用前回到期刊官网核验",
        "role": "自动检索主入口和跨库补检，不替代中文专有数据库",
    },
    {
        "key": "cnki",
        "name": "中国知网（CNKI）",
        "coverage": "中文期刊、学位论文、会议论文、报纸、年鉴等",
        "access": "订阅/机构授权为主",
        "search_url": "https://www.cnki.net/",
        "machine_access": "本项目不模拟登录或抓取；使用网站正常检索",
        "import_path": "Zotero Connector，或导出 EndNote/RefWorks/NoteExpress 后导入 Zotero",
        "role": "综合中文期刊主检库",
    },
    {
        "key": "wanfang",
        "name": "万方数据知识服务平台",
        "coverage": "中文期刊、学位论文、会议论文、标准和科技成果",
        "access": "订阅/机构授权为主",
        "search_url": "https://www.wanfangdata.com.cn/",
        "machine_access": "本项目不模拟登录或抓取；使用网站正常检索",
        "import_path": "Zotero Connector，或使用页面提供的引用格式导出后导入 Zotero",
        "role": "综合查漏、学位论文与会议文献",
    },
    {
        "key": "cqvip",
        "name": "维普中文期刊服务平台",
        "coverage": "中文科技期刊题录与全文服务",
        "access": "订阅/机构授权为主",
        "search_url": "https://www.cqvip.com/",
        "machine_access": "本项目不模拟登录或抓取；使用网站正常检索",
        "import_path": "Zotero Connector，或使用页面提供的引用格式导出后导入 Zotero",
        "role": "中文科技期刊补检与卷期页码核验",
    },
    {
        "key": "pubscholar",
        "name": "PubScholar 公益学术平台",
        "coverage": "科技论文、专利、科学数据和中国科学院特色资源",
        "access": "公益检索；部分全文开放",
        "search_url": "https://pubscholar.cn/",
        "machine_access": "当前以网页检索和合规导入为主",
        "import_path": "Zotero Connector；有 DOI 时再用 Crossref/OpenAlex 补齐元数据",
        "role": "免费发现与开放全文线索",
    },
    {
        "key": "nstl",
        "name": "国家科技图书文献中心（NSTL）",
        "coverage": "科技期刊、会议录、学位论文、科技报告、标准和专利",
        "access": "公益检索；注册用户可按规则申请全文传递",
        "search_url": "https://www.nstl.gov.cn/",
        "machine_access": "个人使用网页；机构数据服务需另行申请授权",
        "import_path": "Zotero Connector或人工录入；保留全文传递申请记录",
        "role": "自然科学与工程科技查漏、馆际/全文传递",
    },
    {
        "key": "ncpssd",
        "name": "国家哲学社会科学文献中心",
        "coverage": "中文/外文社科期刊、集刊、古籍和优先发布论文",
        "access": "公益检索，注册后按平台规则获取全文",
        "search_url": "https://www.ncpssd.cn/",
        "machine_access": "当前以网页高级检索为主",
        "import_path": "Zotero Connector或平台引用导出；人工核验核心期刊范围",
        "role": "人文社会科学主检与开放全文补充",
    },
    {
        "key": "chinaxiv",
        "name": "ChinaXiv 中国科学院科技论文预发布平台",
        "coverage": "自然科学、工程、医学、心理、管理等预印本",
        "access": "开放检索与下载",
        "search_url": "https://chinaxiv.org/",
        "machine_access": "当前以网页检索和元数据导入为主",
        "import_path": "Zotero Connector；记录版本号和发布日期",
        "role": "追踪最新研究；必须标记为未经正式同行评审的预印本",
    },
    {
        "key": "sinomed",
        "name": "SinoMed 中国生物医学文献服务系统",
        "coverage": "中文生物医学期刊、会议与学位论文",
        "access": "以平台当前授权规则为准",
        "search_url": "https://www.sinomed.ac.cn/zh/index.jsp",
        "machine_access": "当前以网页专业检索为主",
        "import_path": "使用平台引用导出或 Zotero Connector；保留主题词检索式",
        "role": "医学、药学、公共卫生和护理学的专业补检",
    },
)


def list_chinese_literature_sources() -> list[ChineseLiteratureSource]:
    """Return a copy of the maintained Chinese-literature source registry."""
    return [source.copy() for source in _CHINESE_LITERATURE_SOURCES]
