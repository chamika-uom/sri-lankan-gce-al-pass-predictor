from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "AML_Assignment_XAI_Report.docx"
OUT = ROOT / "outputs"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_borders(cell, color="D9D9D9", size="6"):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn("w:" + m))
        if node is None:
            node = OxmlElement("w:" + m)
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_keep_with_next(paragraph, value=True):
    p_pr = paragraph._p.get_or_add_pPr()
    node = p_pr.find(qn("w:keepNext"))
    if value and node is None:
        node = OxmlElement("w:keepNext")
        p_pr.append(node)
    elif not value and node is not None:
        p_pr.remove(node)


def set_font(run, name="Arial", size=10.5, color="000000", bold=None, italic=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def style_paragraph(paragraph, space_after=6, line_spacing=1.12, first_line=0):
    fmt = paragraph.paragraph_format
    fmt.keep_together = True
    fmt.space_after = Pt(space_after)
    fmt.line_spacing = line_spacing
    if first_line:
        fmt.first_line_indent = Inches(first_line)


def add_paragraph(doc, text="", style=None, bold_lead=None, space_after=6, first_line=0):
    p = doc.add_paragraph(style=style)
    style_paragraph(p, space_after=space_after, first_line=first_line)
    if bold_lead and text.startswith(bold_lead):
        r = p.add_run(bold_lead)
        set_font(r, bold=True)
        r2 = p.add_run(text[len(bold_lead):])
        set_font(r2)
    else:
        r = p.add_run(text)
        set_font(r)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        style_paragraph(p, space_after=3)
        r = p.add_run(item)
        set_font(r)


def add_link(doc, label, url):
    p = doc.add_paragraph()
    style_paragraph(p)
    set_font(p.add_run(label + ": "), bold=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), p.part.relate_to(url, RT.HYPERLINK, is_external=True))
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    properties.append(color)
    run.append(properties)
    text = OxmlElement("w:t")
    text.text = url
    run.append(text)
    link.append(run)
    p._p.append(link)


def add_numbered(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Number")
        style_paragraph(p, space_after=3)
        r = p.add_run(item)
        set_font(r)


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    set_keep_with_next(p)
    style_paragraph(p, space_after=5 if level == 1 else 3, line_spacing=1.0)
    r = p.add_run(text)
    set_font(r, size=15 if level == 1 else 12, bold=True)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_paragraph(p, space_after=8, line_spacing=1.0)
    r = p.add_run(text)
    set_font(r, size=9, color="555555", italic=True)
    return p


def add_image(doc, filename, width=6.25, alt_text=""):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_paragraph(p, space_after=3, line_spacing=1.0)
    run = p.add_run()
    run.add_picture(str(OUT / filename), width=Inches(width))
    if alt_text:
        drawing = run._r.find(qn("w:drawing"))
        if drawing is not None:
            inline = drawing.find(qn("wp:inline"))
            if inline is not None:
                doc_pr = inline.find(qn("wp:docPr"))
                if doc_pr is not None:
                    doc_pr.set("descr", alt_text)
                    doc_pr.set("title", filename)
    set_keep_with_next(p)
    return p


def add_table(doc, headers, rows, widths=None, header_fill="E7E6E6", font_size=9.1, alignments=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    header = table.rows[0]
    set_repeat_table_header(header)
    for i, h in enumerate(headers):
        cell = header.cells[i]
        if widths:
            cell.width = Inches(widths[i])
        set_cell_shading(cell, header_fill)
        set_cell_borders(cell)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style_paragraph(p, space_after=0, line_spacing=1.0)
        r = p.add_run(str(h))
        set_font(r, size=font_size, color="000000", bold=True)
    for row_index, row_values in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row_values):
            cell = cells[i]
            if widths:
                cell.width = Inches(widths[i])
            set_cell_shading(cell, "FFFFFF")
            set_cell_borders(cell)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.alignment = (alignments[i] if alignments else WD_ALIGN_PARAGRAPH.LEFT)
            style_paragraph(p, space_after=0, line_spacing=1.05)
            r = p.add_run(str(value))
            set_font(r, size=font_size)
    if len(rows) <= 9:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    set_keep_with_next(paragraph)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    set_font(run, size=8, color="666666")
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    paragraph._p.append(fld)


def configure_document(doc):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(0, 0, 0)

    for style_name, size in (("Title", 24), ("Heading 1", 15), ("Heading 2", 12)):
        st = styles[style_name]
        st.font.name = "Arial"
        st._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        st._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)

    for list_name in ("List Bullet", "List Number"):
        st = styles[list_name]
        st.font.name = "Arial"
        st._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        st._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        st.font.size = Pt(10.5)

    footer = section.footer
    p = footer.paragraphs[0]
    p.text = "Applied Machine Learning Assignment"
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    style_paragraph(p, space_after=0, line_spacing=1.0)
    for r in p.runs:
        set_font(r, size=8, color="666666")
    add_page_number(footer.add_paragraph())


def add_cover(doc):
    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(92)
    p.paragraph_format.space_after = Pt(22)
    r = p.add_run("Explainable Machine Learning for Predicting General English Pass Results")
    set_font(r, size=23, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_paragraph(p, space_after=18, line_spacing=1.0)
    r = p.add_run("Applied Machine Learning Assignment Report")
    set_font(r, size=14, color="000000", bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_paragraph(p, space_after=4, line_spacing=1.0)
    r = p.add_run("MSc in Artificial Intelligence")
    set_font(r, size=11)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_paragraph(p, space_after=4, line_spacing=1.0)
    r = p.add_run("28 October 2026")
    set_font(r, size=11)

    doc.add_page_break()


def build_report():
    metrics = pd.read_csv(OUT / "model_metrics.csv")
    summary = json.loads((OUT / "run_summary.json").read_text())
    shap_local = pd.read_csv(OUT / "shap_local_values.csv")
    lime_local = pd.read_csv(OUT / "lime_local_values.csv")
    best_name = summary["best_model"]
    best_row = metrics.loc[metrics["model"] == best_name].iloc[0]
    nb_row = metrics.loc[metrics["model"] == "Categorical Naive Bayes"].iloc[0]
    positive_shap = shap_local[shap_local["shap_value"] > 0]
    negative_shap = shap_local[shap_local["shap_value"] < 0]
    positive_example = positive_shap.iloc[0] if not positive_shap.empty else shap_local.iloc[0]
    negative_example = negative_shap.iloc[0] if not negative_shap.empty else shap_local.iloc[-1]

    doc = Document()
    configure_document(doc)
    add_cover(doc)

    add_heading(doc, "Abstract")
    add_paragraph(
        doc,
        "This assignment examines the prediction of General English results using Sri Lankan GCE Advanced Level examination data from 2020. The model uses the candidate's A/L stream, syllabus, three selected subjects, and grades in those subjects. It does not use names, ranks, birth details, or gender.",
    )
    add_paragraph(
        doc,
        f"Three models were compared on a held-out test set: Random Forest, XGBoost, and Categorical Naive Bayes. Categorical Naive Bayes was selected for the new-algorithm component of the assignment. It achieved {nb_row['accuracy'] * 100:.2f}% accuracy and {nb_row['f1_macro']:.3f} macro F1. {best_name} achieved the highest accuracy, macro F1 and ROC AUC.",
    )
    add_paragraph(
        doc,
        "SHAP and LIME were used to examine the predictions of Categorical Naive Bayes. The SHAP results indicate that subject choices and grades contributed more to its predictions than the syllabus field.",
    )

    add_heading(doc, "Problem description")
    add_paragraph(
        doc,
        "The aim is to examine how well the other A/L subjects and grades predict the General English result, and to identify which inputs influence the predictions. As the inputs include grades from the same examination, this analysis cannot provide an early warning before those results are available.",
    )
    add_paragraph(
        doc,
        "The General English result was grouped into two classes. A General English grade of A, B, C, or S is labelled Pass. A grade of F, Absent, or Withheld is labelled Non-pass. The prediction task is therefore binary classification.",
    )

    add_heading(doc, "Dataset and ethical use")
    add_paragraph(
        doc,
        "The source is the Student Performance GCE A/L Exam 2020 Sri Lanka dataset, collected from the Sri Lankan Department of Examinations result site and published by Sasika Amarasinghe on Kaggle. An 80,000-row stratified sample was used to reduce computation time.",
    )
    add_table(
        doc,
        ["Item", "Description"],
        [
            ["Rows used", "80,000"],
            ["Input features", "8 categorical fields"],
            ["Target", "Pass or Non-pass in General English"],
            ["Pass records", "34,979"],
            ["Non-pass records", "45,021"],
            ["Missing values", "35,752 missing stream values; other selected fields have no missing values after cleaning"],
        ],
        widths=[1.55, 5.6],
    )
    add_paragraph(doc, "The model uses the following fields:")
    add_table(
        doc,
        ["Field", "Meaning"],
        [
            ["stream", "A/L stream such as Arts, Commerce, or Physical Science"],
            ["syllabus", "New or old syllabus"],
            ["sub1, sub2, sub3", "The three selected A/L subjects"],
            ["sub1_r, sub2_r, sub3_r", "The grade letter for each selected subject"],
            ["ge_r", "General English grade used to create the target; it is not used as an input"],
        ],
        widths=[1.55, 5.6],
    )
    add_paragraph(
        doc,
        "Identifiers, rank columns, birth information and gender were excluded from the input features to reduce privacy concerns and possible data leakage.",
    )
    add_image(doc, "eda_class_distribution.png", width=6.15, alt_text="Bar chart showing 34,979 Pass records and 45,021 Non-pass records.")
    add_caption(doc, "Figure 1. Distribution of the two target classes in the 80,000-row sample.")

    add_heading(doc, "Methodology")
    add_heading(doc, "Data preparation", level=2)
    add_numbered(
        doc,
        [
            "Load the selected columns from the CSV file and replace special missing-value markers with missing values.",
            "Create the binary target from the General English grade. Pass is encoded as 1 and Non-pass as 0.",
            "Fill missing categorical values with the label Unknown for model training and the application.",
            "Use a stratified 80% training and 20% test split. Stratification keeps the Pass and Non-pass proportions similar in both parts.",
        ],
    )
    add_paragraph(doc, "The split contains 64,000 training rows and 16,000 held-out test rows. The test set was not used to tune the final models.")

    add_heading(doc, "Models used", level=2)
    add_table(
        doc,
        ["Model", "Description", "Use in the assignment"],
        [
            ["Random Forest", "Builds many decision trees using different samples and features, then combines their votes.", "Baseline model"],
            ["XGBoost", "Builds small trees one after another, with each new tree correcting earlier errors.", "Comparison model; strongest test result"],
            ["Categorical Naive Bayes", "Uses the probability of each category and combines these probabilities to classify a record.", "New algorithm selected for the assignment"],
        ],
        widths=[1.25, 4.4, 1.5],
        font_size=8.8,
    )
    add_paragraph(
        doc,
        "Random Forest and XGBoost use a pipeline that imputes categories, performs one-hot encoding, and applies sparse-safe standardisation. Categorical Naive Bayes uses ordinal category codes, where each category is represented by an integer. A small randomized search tuned Random Forest and XGBoost using macro F1. The selected settings were Random Forest with 200 trees, maximum depth 18, minimum leaf size 2, and square-root feature sampling; and XGBoost with 280 trees, depth 7, learning rate 0.04, subsample 0.75, and column subsampling 0.75. Categorical Naive Bayes used Laplace smoothing with alpha equal to 1.0.",
    )

    add_heading(doc, "Evaluation measures", level=2)
    add_table(
        doc,
        ["Measure", "Definition"],
        [
            ["Accuracy", "The proportion of all test cases classified correctly."],
            ["Macro precision", "Average precision across Pass and Non-pass, giving both classes equal weight."],
            ["Macro recall", "Average ability to find each class, giving both classes equal weight."],
            ["Macro F1", "A combined score that balances precision and recall across the two classes."],
            ["ROC AUC", "How well the model ranks Pass above Non-pass across probability thresholds."],
        ],
        widths=[1.55, 5.6],
    )

    add_heading(doc, "Explainable AI methods")
    add_paragraph(
        doc,
        "Explainable Artificial Intelligence (XAI) methods help interpret model predictions. Global explanations describe patterns across several records, while local explanations describe an individual prediction. This assignment uses SHAP for both levels and LIME for a local explanation.",
    )
    add_table(
        doc,
        ["Technique", "Description", "Level", "Used here"],
        [
            ["Feature importance", "Ranks features by how much the model relies on them overall.", "Global", "Yes, through the SHAP summary"],
            ["SHAP", "Shares a model output between input features relative to a baseline. Positive values push toward the explained class; negative values push away.", "Global and local", "Yes"],
            ["LIME", "Creates nearby versions of one case and fits a simple local model to explain that case.", "Local", "Yes"],
            ["PDP", "Shows the average model prediction as one feature changes across the data.", "Global effect", "Not implemented"],
            ["Permutation importance", "Shuffles one feature and measures how much test performance falls.", "Global reliance", "Not implemented"],
            ["Counterfactual explanation", "Describes a small feasible change that could lead to a different prediction.", "Local recourse", "Not implemented"],
        ],
        widths=[1.2, 3.8, 1.0, 1.15],
        font_size=8.4,
    )
    add_paragraph(
        doc,
        "Both methods were applied to Categorical Naive Bayes because it was the algorithm selected for further study. SHAP estimates each feature's contribution relative to a baseline prediction. LIME fits an interpretable model around one record to approximate the classifier's behaviour nearby.",
    )

    add_heading(doc, "Results")
    add_heading(doc, "Model comparison", level=2)
    metric_rows = []
    for _, row in metrics.iterrows():
        metric_rows.append([
            row["model"],
            f"{row['accuracy'] * 100:.2f}%",
            f"{row['precision_macro'] * 100:.2f}%",
            f"{row['recall_macro'] * 100:.2f}%",
            f"{row['f1_macro']:.3f}",
            f"{row['roc_auc']:.3f}",
        ])
    add_table(
        doc,
        ["Model", "Accuracy", "Macro precision", "Macro recall", "Macro F1", "ROC AUC"],
        metric_rows,
        widths=[1.35, 1.05, 1.25, 1.2, 0.95, 0.95],
        font_size=8.7,
        alignments=[WD_ALIGN_PARAGRAPH.LEFT] + [WD_ALIGN_PARAGRAPH.CENTER] * 5,
    )
    add_paragraph(
        doc,
        f"{best_name} produced the highest accuracy, macro F1, and ROC AUC in this run. Its accuracy was {best_row['accuracy'] * 100:.2f}%. Categorical Naive Bayes achieved {nb_row['accuracy'] * 100:.2f}% accuracy and {nb_row['f1_macro']:.3f} macro F1. These scores describe performance on this test split; they do not establish how the models would compare on another cohort.",
    )
    add_image(doc, "model_comparison.png", width=6.2, alt_text="Grouped bar chart comparing accuracy, macro F1, and ROC AUC for Random Forest, XGBoost, and Categorical Naive Bayes.")
    add_caption(doc, "Figure 2. Accuracy, macro F1, and ROC AUC on the held-out test set.")

    add_heading(doc, "XGBoost confusion matrix", level=2)
    add_paragraph(
        doc,
        f"The confusion matrix for {best_name} contains 11,994 correct predictions and 4,006 errors across the 16,000 test records. It incorrectly predicted Pass for 2,177 Non-pass records and Non-pass for 1,829 Pass records.",
    )
    set_keep_with_next(doc.paragraphs[-1])
    add_image(doc, "confusion_matrix.png", width=4.5, alt_text="XGBoost confusion matrix with 6,827 correct Non-pass predictions, 2,177 false Pass predictions, 1,829 false Non-pass predictions, and 5,167 correct Pass predictions.")
    add_caption(doc, "Figure 3. XGBoost confusion matrix on 16,000 held-out test cases.")

    add_heading(doc, "Example of one prediction", level=2)
    add_paragraph(
        doc,
        "One held-out test record contained an Unknown stream, the new syllabus, Geography with grade F, History of Sri Lanka and Europe with grade S, and Islamic Civilization with grade C. XGBoost predicted Non-pass with a Pass probability of 0.216. The actual target for this row was Non-pass. This prediction illustrates the output for one test record.",
    )

    add_heading(doc, "Interpretation with XAI")
    add_heading(doc, "Global SHAP explanation", level=2)
    add_paragraph(
        doc,
        "The global SHAP chart is based on Categorical Naive Bayes and a sample of 120 test rows. Each bar is the mean absolute SHAP value. A longer bar means that the feature usually changes the model's predicted Pass probability more strongly, regardless of whether the change is positive or negative for a particular student.",
    )
    add_image(doc, "shap_summary.png", width=6.15, alt_text="Horizontal SHAP importance chart ranking sub1, sub3, sub2, stream, sub1_r, sub2_r, sub3_r, and syllabus.")
    add_caption(doc, "Figure 4. Global SHAP feature importance for Categorical Naive Bayes.")
    add_paragraph(
        doc,
        "The first subject field (sub1) has the highest mean absolute SHAP value, followed by the third and second subject fields. The syllabus field has the lowest value. These results suggest that the model relied more on subjects and grades than on whether a candidate followed the old or new syllabus.",
    )

    add_heading(doc, "Local SHAP example", level=2)
    add_paragraph(
        doc,
        f"For one sampled test case, the largest positive contribution in the saved explanation was {positive_example['feature']} with value {positive_example['value']}. The largest negative contribution was {negative_example['feature']} with value {negative_example['value']}. A positive value pushed the Categorical Naive Bayes predicted Pass probability upward relative to its baseline, while a negative value pushed it downward. SHAP values are contributions to the model output, not causal effects.",
    )
    shap_rows = [[r["feature"], f"{r['shap_value']:+.3f}", r["value"]] for _, r in shap_local.iterrows()]
    add_table(
        doc,
        ["Feature", "SHAP value", "Observed value"],
        shap_rows,
        widths=[1.5, 1.2, 4.25],
        font_size=8.8,
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
    )

    add_heading(doc, "Local LIME example", level=2)
    add_paragraph(
        doc,
        "LIME explains one case by creating nearby categorical versions of the case, asking Categorical Naive Bayes for predictions, and fitting a simple local surrogate. The table shows the largest local weights returned by the analysis. Positive weights support the selected class in this local surrogate; negative weights oppose it. These weights should not be interpreted as global coefficients.",
    )
    lime_rows = [[r["feature"], f"{r['weight']:+.3f}"] for _, r in lime_local.iterrows()]
    add_table(
        doc,
        ["Local condition", "LIME weight"],
        lime_rows,
        widths=[5.8, 1.15],
        font_size=8.8,
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER],
    )
    add_paragraph(
        doc,
        "The two tables describe individual test cases. Their feature contributions may differ from the global ranking because the influence of a feature depends on the values in each record.",
    )

    add_heading(doc, "Discussion")
    add_heading(doc, "Model performance", level=2)
    add_paragraph(
        doc,
        "All three models achieved test accuracy between 73.94% and 74.96%. For comparison, predicting Non-pass for every test record would give 56.28% accuracy. XGBoost performed best on accuracy, macro F1 and ROC AUC, although Random Forest had the highest macro recall. Categorical Naive Bayes was only about one percentage point below XGBoost in accuracy. Its assumption of conditional independence may be restrictive here because subject choices and grades can be related. However, the results alone do not show whether this assumption explains the difference in performance.",
    )
    add_heading(doc, "Limitations", level=2)
    add_bullets(
        doc,
        [
            "The project uses a sample of the 2020 examination data, so the findings may not represent later cohorts, different regions, or different examinations.",
            "The stream field contains many missing values. Treating missing stream as Unknown avoids dropping rows, but Unknown is not a real academic stream and may carry data-collection information.",
            "The target is based on the General English result and the inputs include other subject grades from the same examination. This is useful for prediction after results are available, but it is not an early-warning model before those grades are known.",
            "The dataset contains categorical records and does not include factors such as attendance, study time, school resources, language background, or household circumstances. Missing variables may limit performance and interpretation.",
            "SHAP and LIME explain the fitted model. They do not establish causation, fairness, or that the model will work equally well for every subgroup.",
        ],
    )
    add_heading(doc, "Bias and ethical considerations", level=2)
    add_paragraph(
        doc,
        "The dataset may reflect differences in educational opportunities. Excluding gender does not establish that the model is fair, since subject choices and streams may also be associated with students' backgrounds. Subgroup performance was not evaluated in this assignment, so the overall accuracy cannot show whether errors are distributed equally. Further evaluation would be needed before using these predictions in educational decisions.",
    )
    add_heading(doc, "Front end integration", level=2)
    add_paragraph(
        doc,
        "A Streamlit application was developed for the optional front-end component. It accepts the eight input fields and displays the XGBoost Pass or Non-pass prediction and estimated Pass probability. SHAP and LIME explanations for Categorical Naive Bayes are saved separately in the project outputs. The application is a demonstration using the available examination data.",
    )
    add_link(doc, "GitHub repository", "https://github.com/chamika-uom/sri-lankan-gce-al-pass-predictor")
    add_link(doc, "Streamlit application", "https://sri-lankan-gce-al-pass-predictor-newcvcucpbcffyc7cfkabw.streamlit.app/")

    doc.add_page_break()
    add_heading(doc, "Conclusion")
    add_paragraph(
        doc,
        f"This assignment compared Random Forest, XGBoost and Categorical Naive Bayes for predicting General English Pass and Non-pass results. {best_name} achieved the highest test accuracy at {best_row['accuracy'] * 100:.2f}%, compared with {nb_row['accuracy'] * 100:.2f}% for Categorical Naive Bayes. The SHAP analysis showed that subjects and grades contributed most to the Naive Bayes predictions, while LIME provided a local explanation for an individual case.",
    )
    add_paragraph(
        doc,
        "The results are limited to the sampled 2020 records and the available categorical features. Testing on a later cohort would help assess whether the performance is consistent. A future study aimed at early prediction would also need inputs collected before the examination results are released.",
    )

    add_heading(doc, "References")
    refs = [
        "Machine Learning Assignment Guidelines MSc in AI. Supplied course document.",
        "Explainable AI Lecture Note. Supplied lecture note, prepared 11 October 2026.",
        "Ribeiro, M. T., Singh, S., and Guestrin, C. (2016). Why Should I Trust You? Explaining the Predictions of Any Classifier. KDD.",
        "XGBoost Algorithm. Supplied lecture slides. Covers boosting, gradient boosting, and XGBoost.",
        "LIME XAI Lecture Notes. Supplied course material on Local Interpretable Model-agnostic Explanations.",
        "Amarasinghe, S. Student Performance GCE A/L Exam 2020 Sri Lanka dataset, published on Kaggle. The project README records the source description and dataset link.",
        "Project source code and outputs: src/train_model.py, notebooks/assignment_notebook_executed.ipynb, data/DATA_DICTIONARY.md, and outputs/.",
    ]
    for i, ref in enumerate(refs, start=1):
        p = doc.add_paragraph()
        style_paragraph(p, space_after=4)
        r = p.add_run(f"{i}. ")
        set_font(r, size=9.5, bold=True)
        r2 = p.add_run(ref)
        set_font(r2, size=9.5)

    for style in doc.styles:
        for border in list(style.element.iter(qn("w:pBdr"))):
            border.getparent().remove(border)
    for paragraph in doc.paragraphs:
        for border in list(paragraph._p.iter(qn("w:pBdr"))):
            border.getparent().remove(border)
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build_report()
