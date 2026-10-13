from app.models import Ground, Source
from app.research.tavily import save_sources, search_official

# ponytail: one fixed query per category; have the agent tier write queries once grounds go beyond these two.
QUERIES = {
    "output_tax_r1_vs_3b": "GSTR-1 GSTR-3B difference output tax liability credit note section 34 scrutiny ASMT-10 clarification",
    "itc_2b_vs_3b": "input tax credit GSTR-3B exceeds GSTR-2B section 16(2)(aa) supplier not filed circular clarification",
}


def research(case_id: str, g: Ground) -> list[Source]:
    q = QUERIES[g.category]
    return save_sources(case_id, g.ground_no, q, search_official(q))
