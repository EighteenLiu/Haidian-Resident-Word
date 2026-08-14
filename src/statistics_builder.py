from __future__ import annotations

from collections import Counter, defaultdict

from .models import (
    AnalysisItem,
    CaseRecord,
    CategoryRow,
    IndicatorMapping,
    ProblemTypeRow,
    ReportStats,
    TownRow,
    ValidationWarning,
    VillageEntry,
    VillageRow,
)
from .utils import natural_join, normalize_text, pct_text


def _clean_village(record: CaseRecord, villages_by_norm: dict[str, VillageEntry]) -> tuple[str, str]:
    town = record.point_level_2 or record.street_center
    village = record.point_level_3
    norm_village = normalize_text(village)
    for entry in villages_by_norm.values():
        nv = normalize_text(entry.village_name)
        nt = normalize_text(entry.town_name)
        if norm_village == nv or norm_village == normalize_text(entry.town_name + entry.village_name) or norm_village.endswith(nv):
            return entry.town_name, entry.village_name
        if normalize_text(town) == nt and nv in norm_village:
            return entry.town_name, entry.village_name
    return town, village


def _category_bucket(category: str) -> str:
    if category == "村容村貌整治":
        return "village_appearance_count"
    if category == "农村生活污水":
        return "sewage_count"
    if category == "农村厕所革命":
        return "toilet_count"
    return "garbage_count"


def build_report_stats(
    records: list[CaseRecord],
    villages: list[VillageEntry],
    indicator_mappings: dict[str, IndicatorMapping],
    rules: dict,
) -> ReportStats:
    total = len(records)
    category_order = rules.get("statistics", {}).get(
        "category_order",
        ["农村生活垃圾治理", "村容村貌整治", "农村生活污水", "农村厕所革命"],
    )
    village_by_norm = {normalize_text(v.village_name): v for v in villages}
    town_order = []
    for v in villages:
        if v.town_name not in town_order:
            town_order.append(v.town_name)

    category_counts = Counter()
    problem_counts = Counter()
    town_counts = Counter()
    village_category_counts: dict[tuple[str, str], Counter] = defaultdict(Counter)
    village_subcategory_counts: dict[tuple[str, str], Counter] = defaultdict(Counter)
    category_village_counts: dict[str, Counter] = defaultdict(Counter)
    problem_village_counts: dict[str, Counter] = defaultdict(Counter)
    unmapped = Counter()
    village_unknown = Counter()

    for record in records:
        town, village = _clean_village(record, village_by_norm)
        mapping = indicator_mappings.get(normalize_text(record.indicator_level_3))
        if not mapping:
            unmapped[record.indicator_level_3 or "(空指标)"] += 1
            category = "未映射"
            subcategory = "未映射"
        else:
            category = mapping.category_name
            subcategory = mapping.subcategory_name
        category_counts[category] += 1
        problem_counts[(category, record.indicator_level_3)] += 1
        town_counts[town] += 1
        village_category_counts[(town, village)][category] += 1
        village_subcategory_counts[(town, village)][subcategory] += 1
        category_village_counts[category][(town, village)] += 1
        problem_village_counts[record.indicator_level_3][(town, village)] += 1
        if normalize_text(village) not in village_by_norm:
            village_unknown[village] += 1

    category_rows: list[CategoryRow] = []
    seq = 1
    for category in category_order:
        count = category_counts.get(category, 0)
        category_rows.append(CategoryRow(seq, category, count, count / total if total else 0, pct_text(count, total)))
        seq += 1
    for category, count in sorted(category_counts.items()):
        if category not in category_order:
            category_rows.append(CategoryRow(seq, category, count, count / total if total else 0, pct_text(count, total)))
            seq += 1
    category_rows.append(CategoryRow("总计", "总计", total, 1 if total else 0, "100.00%" if total else "0.00%"))

    sorted_problem_items = sorted(problem_counts.items(), key=lambda kv: (-kv[1], str(kv[0][1])))
    problem_type_rows = [
        ProblemTypeRow(i, category, problem, count, count / total if total else 0, pct_text(count, total))
        for i, ((category, problem), count) in enumerate(sorted_problem_items, 1)
    ]

    ordered_towns = [town for town in town_order if town_counts.get(town, 0)] + sorted(t for t in town_counts if t not in town_order)
    town_rows = [
        TownRow(i, town, town_counts[town], town_counts[town] / total if total else 0, pct_text(town_counts[town], total))
        for i, town in enumerate(ordered_towns, 1)
    ]

    village_rows: list[VillageRow] = []
    for town in ordered_towns:
        rows = [(key, counts) for key, counts in village_category_counts.items() if key[0] == town and sum(counts.values()) > 0]
        rows.sort(key=lambda item: (-sum(item[1].values()), item[0][1]))
        for (town_name, village_name), counts in rows:
            village_rows.append(
                VillageRow(
                    town_name=town_name,
                    village_name=village_name,
                    garbage_count=counts.get("农村生活垃圾治理", 0),
                    village_appearance_count=counts.get("村容村貌整治", 0),
                    sewage_count=counts.get("农村生活污水", 0),
                    toilet_count=counts.get("农村厕所革命", 0),
                    total_count=sum(counts.values()),
                )
            )

    warnings: list[ValidationWarning] = []
    for indicator, count in sorted(unmapped.items(), key=lambda kv: (-kv[1], kv[0])):
        warnings.append(ValidationWarning("UNMAPPED_INDICATOR", f"未映射指标：{indicator}（{count}条）", {"indicator": indicator, "count": count}))
    for village, count in sorted(village_unknown.items(), key=lambda kv: (-kv[1], kv[0])):
        warnings.append(ValidationWarning("VILLAGE_NOT_IN_DICT", f"村庄不在字典：{village}（{count}条）", {"village": village, "count": count}))

    rounds = int(rules.get("inspection", {}).get("rounds", 2) or 2)
    resolved = sum(1 for r in records if r.is_solved == "是")

    return ReportStats(
        total_problem_count=total,
        resolved_count=resolved,
        resolved_rate=resolved / total if total else 0,
        average_per_round=round(total / rounds) if rounds else total,
        category_rows=category_rows,
        problem_type_rows=problem_type_rows,
        town_rows=town_rows,
        village_rows=village_rows,
        category_analysis_items=_build_category_analysis(category_rows, category_village_counts, total),
        high_frequency_problem_items=_build_high_frequency(problem_type_rows, problem_village_counts, total),
        validation_warnings=warnings,
        village_indicator_counts={key: dict(counter) for key, counter in village_subcategory_counts.items()},
        unmapped_indicator_counts=dict(unmapped),
    )


def _top_villages_text(counter: Counter, limit: int = 3) -> str:
    if not counter:
        return ""
    parts = []
    for (town, village), count in counter.most_common(limit):
        parts.append(f"{town}{village}（{count}个）")
    return "主要集中在" + "、".join(parts)


def _build_category_analysis(category_rows: list[CategoryRow], category_village_counts: dict[str, Counter], total: int) -> list[AnalysisItem]:
    items = []
    for row in category_rows:
        if row.name == "总计":
            continue
        items.append(AnalysisItem(row.name, row.count, row.rate_text, _top_villages_text(category_village_counts.get(row.name, Counter()))))
    return items


def _build_high_frequency(problem_rows: list[ProblemTypeRow], problem_village_counts: dict[str, Counter], total: int) -> list[AnalysisItem]:
    items = []
    for row in problem_rows[:3]:
        items.append(AnalysisItem(row.problem_name, row.count, row.rate_text, _top_villages_text(problem_village_counts.get(row.problem_name, Counter()))))
    return items


def summarize_towns(town_rows: list[TownRow]) -> str:
    return "，".join(f"{row.town_name}发现问题{row.count}个，占比{row.rate_text}" for row in town_rows)


def summarize_villages(village_rows: list[VillageRow]) -> str:
    by_town: dict[str, list[VillageRow]] = defaultdict(list)
    for row in village_rows:
        by_town[row.town_name].append(row)
    sentences = []
    for town, rows in by_town.items():
        top = rows[:3]
        if not top:
            continue
        if len(top) >= 3 and top[1].total_count == top[2].total_count:
            text = f"{top[0].village_name}{top[0].total_count}个，{top[1].village_name}和{top[2].village_name}各{top[1].total_count}个"
        else:
            text = "、".join(f"{r.village_name}{r.total_count}个" for r in top[:2])
        sentences.append(f"{town}问题较多的村为{text}")
    return "，".join(sentences)
