/**
 * Regulation 法规问答模块类型 —— v0.1 D5.
 * Mirror of backend `RegulationSnippetPayload` in `interfaces.py`.
 */

export type RegulationCategory = "VAT" | "CIT" | "IIT" | "CAS";

export type RegulationSnippetPayload = {
  reg_id: string;
  source_name: string;
  chapter: string;
  article_number: string;
  summary: string;
  full_text: string;
  category: RegulationCategory;
};
