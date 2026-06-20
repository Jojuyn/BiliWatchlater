"""Bilibili category_v2 mapping constants for display grouping."""

from __future__ import annotations

from pathlib import Path
import sqlite3


# parent_category_v2 → display group
PARENT_GROUP_MAP: dict[str, str] = {
    "知识": "成长",
    "人工智能": "AI",
    "游戏": "游戏",
    "二次元": "娱乐",
    "科技数码": "技术",
    "音乐": "娱乐",
    "影视": "影视",
    "vlog": "生活",
    "时尚美妆": "穿搭",
    "旅游出行": "旅游",
    "美食": "美食",
    "情感": "成长",
    "健身": "健身",
    "资讯": "资讯",
    "体育运动": "运动",
    "小剧场": "娱乐",
    "神秘学": "其他",
    "三农": "生活",
    "绘画": "娱乐",
    "动物": "其他",
    "医疗保健": "其他",
    "生活经验": "生活",
    "鬼畜": "娱乐",
    "汽车": "其他",
    "户外潮流": "旅游",
    "舞蹈": "娱乐",
    "娱乐": "娱乐",
    "亲子": "成长",
    "家装房产": "其他",
}


CATEGORY_MAP: dict[str, dict] = {
    "计算机技术": {"tag": "编程", "color": "#22c55e", "group": "学习"},
    "AI学习": {"tag": "AI", "color": "#a855f7", "group": "学习"},
    "校园学习": {"tag": "校园学习", "color": "#06b6d4", "group": "学习"},
    "科学科普": {"tag": "科普", "color": "#10b981", "group": "学习"},
    "应试教育": {"tag": "应试", "color": "#06b6d4", "group": "学习"},
    "大学专业知识": {"tag": "大学专业", "color": "#06b6d4", "group": "学习"},
    "非应试语言学习": {"tag": "语言", "color": "#06b6d4", "group": "学习"},
    "绘画学习": {"tag": "绘画学习", "color": "#06b6d4", "group": "学习"},
    "AI杂谈": {"tag": "AI", "color": "#a855f7", "group": "AI"},
    "AI影视": {"tag": "AI", "color": "#a855f7", "group": "AI"},
    "AI资讯": {"tag": "AI", "color": "#a855f7", "group": "AI"},
    "AI音乐": {"tag": "AI", "color": "#a855f7", "group": "AI"},
    "商业财经": {"tag": "财经", "color": "#eab308", "group": "成长"},
    "社会观察": {"tag": "社会", "color": "#f97316", "group": "成长"},
    "职场发展": {"tag": "职场", "color": "#f97316", "group": "成长"},
    "心理杂谈": {"tag": "心理", "color": "#f97316", "group": "成长"},
    "人文历史": {"tag": "人文历史", "color": "#f97316", "group": "成长"},
    "时政解读": {"tag": "时政", "color": "#ef4444", "group": "成长"},
    "自我成长": {"tag": "自我成长", "color": "#f97316", "group": "成长"},
    "恋爱关系": {"tag": "情感", "color": "#ec4899", "group": "成长"},
    "人际关系": {"tag": "社交", "color": "#ec4899", "group": "成长"},
    "家庭关系": {"tag": "家庭", "color": "#ec4899", "group": "成长"},
    "亲子教育": {"tag": "亲子", "color": "#ec4899", "group": "成长"},
    "工程机械": {"tag": "工程机械", "color": "#64748b", "group": "技术"},
    "电脑": {"tag": "电脑", "color": "#3b82f6", "group": "技术"},
    "手机": {"tag": "手机", "color": "#3b82f6", "group": "技术"},
    "科技数码综合": {"tag": "科技数码", "color": "#64748b", "group": "技术"},
    "摄影摄像": {"tag": "摄影", "color": "#64748b", "group": "技术"},
    "设计艺术": {"tag": "设计", "color": "#8b5cf6", "group": "技术"},
    "射击游戏": {"tag": "射击", "color": "#ef4444", "group": "游戏"},
    "其他游戏": {"tag": "游戏", "color": "#ef4444", "group": "游戏"},
    "单机主机类游戏": {"tag": "单机主机", "color": "#ef4444", "group": "游戏"},
    "音游舞游": {"tag": "音游", "color": "#ef4444", "group": "游戏"},
    "沙盒类": {"tag": "沙盒", "color": "#ef4444", "group": "游戏"},
    "回合制策略游戏": {"tag": "策略", "color": "#ef4444", "group": "游戏"},
    "动作竞技游戏": {"tag": "动作", "color": "#ef4444", "group": "游戏"},
    "休闲/小游戏": {"tag": "休闲", "color": "#ef4444", "group": "游戏"},
    "MOBA游戏": {"tag": "MOBA", "color": "#ef4444", "group": "游戏"},
    "MMORPG游戏": {"tag": "MMO", "color": "#ef4444", "group": "游戏"},
    "虚拟UP主": {"tag": "VUP", "color": "#ec4899", "group": "娱乐"},
    "原创音乐": {"tag": "原创音乐", "color": "#f43f5e", "group": "娱乐"},
    "音乐教学": {"tag": "音乐教学", "color": "#f43f5e", "group": "娱乐"},
    "电台·歌单": {"tag": "电台", "color": "#f43f5e", "group": "娱乐"},
    "音乐现场": {"tag": "现场", "color": "#f43f5e", "group": "娱乐"},
    "乐评盘点": {"tag": "乐评", "color": "#f43f5e", "group": "娱乐"},
    "翻唱": {"tag": "翻唱", "color": "#f43f5e", "group": "娱乐"},
    "音乐综合": {"tag": "音乐", "color": "#f43f5e", "group": "娱乐"},
    "MV": {"tag": "MV", "color": "#f43f5e", "group": "娱乐"},
    "演奏": {"tag": "演奏", "color": "#f43f5e", "group": "娱乐"},
    "鬼畜综合": {"tag": "鬼畜", "color": "#84cc16", "group": "娱乐"},
    "语言类小剧场": {"tag": "小剧场", "color": "#84cc16", "group": "娱乐"},
    "宅舞": {"tag": "宅舞", "color": "#ec4899", "group": "娱乐"},
    "娱乐评论": {"tag": "娱乐评论", "color": "#84cc16", "group": "娱乐"},
    "同人动画": {"tag": "同人", "color": "#ec4899", "group": "娱乐"},
    "动漫剪辑": {"tag": "动漫", "color": "#ec4899", "group": "娱乐"},
    "动漫评论": {"tag": "动漫", "color": "#ec4899", "group": "娱乐"},
    "动画配音": {"tag": "配音", "color": "#ec4899", "group": "娱乐"},
    "动漫资讯": {"tag": "动漫", "color": "#ec4899", "group": "娱乐"},
    "动漫reaction": {"tag": "动漫", "color": "#ec4899", "group": "娱乐"},
    "二次元绘画": {"tag": "二次元", "color": "#ec4899", "group": "娱乐"},
    "非二次元绘画": {"tag": "绘画", "color": "#84cc16", "group": "娱乐"},
    "特摄": {"tag": "特摄", "color": "#ec4899", "group": "娱乐"},
    "随拍综合": {"tag": "随拍", "color": "#64748b", "group": "生活"},
    "学生vlog": {"tag": "学生日常", "color": "#14b8a6", "group": "生活"},
    "中外生活vlog": {"tag": "生活vlog", "color": "#14b8a6", "group": "生活"},
    "其他vlog": {"tag": "vlog", "color": "#14b8a6", "group": "生活"},
    "职业vlog": {"tag": "职业vlog", "color": "#14b8a6", "group": "生活"},
    "城市出行": {"tag": "出行", "color": "#14b8a6", "group": "生活"},
    "徒步": {"tag": "徒步", "color": "#14b8a6", "group": "生活"},
    "公共交通": {"tag": "交通", "color": "#14b8a6", "group": "生活"},
    "生活技能": {"tag": "生活技能", "color": "#14b8a6", "group": "生活"},
    "办事流程": {"tag": "办事", "color": "#14b8a6", "group": "生活"},
    "婚嫁": {"tag": "婚嫁", "color": "#ec4899", "group": "生活"},
    "农村生活": {"tag": "农村", "color": "#14b8a6", "group": "生活"},
    "农业技术": {"tag": "农技", "color": "#22c55e", "group": "生活"},
    "鞋服穿搭": {"tag": "穿搭", "color": "#f472b6", "group": "穿搭"},
    "美妆": {"tag": "美妆", "color": "#f472b6", "group": "穿搭"},
    "时尚解读": {"tag": "时尚", "color": "#f472b6", "group": "穿搭"},
    "时尚综合": {"tag": "时尚", "color": "#f472b6", "group": "穿搭"},
    "仿妆cos": {"tag": "仿妆", "color": "#f472b6", "group": "穿搭"},
    "美食探店": {"tag": "探店", "color": "#f59e0b", "group": "美食"},
    "美食记录": {"tag": "美食", "color": "#f59e0b", "group": "美食"},
    "美食制作": {"tag": "烹饪", "color": "#f59e0b", "group": "美食"},
    "美食综合": {"tag": "美食", "color": "#f59e0b", "group": "美食"},
    "美食测评": {"tag": "美食测评", "color": "#f59e0b", "group": "美食"},
    "健身科普": {"tag": "健身", "color": "#10b981", "group": "健身"},
    "健身身材展示": {"tag": "健身", "color": "#10b981", "group": "健身"},
    "旅游记录": {"tag": "旅游", "color": "#3b82f6", "group": "旅游"},
    "户外探险": {"tag": "户外", "color": "#3b82f6", "group": "旅游"},
    "影视正片搬运": {"tag": "影视", "color": "#8b5cf6", "group": "影视"},
    "影视剪辑": {"tag": "影视", "color": "#8b5cf6", "group": "影视"},
    "影视解读": {"tag": "影视", "color": "#8b5cf6", "group": "影视"},
    "短剧短片": {"tag": "短剧", "color": "#8b5cf6", "group": "影视"},
    "影视资讯": {"tag": "影视", "color": "#8b5cf6", "group": "影视"},
    "影视综合": {"tag": "影视", "color": "#8b5cf6", "group": "影视"},
    "时政资讯": {"tag": "时政", "color": "#ef4444", "group": "资讯"},
    "综合资讯": {"tag": "资讯", "color": "#64748b", "group": "资讯"},
    "社会资讯": {"tag": "资讯", "color": "#64748b", "group": "资讯"},
    "海外资讯": {"tag": "资讯", "color": "#64748b", "group": "资讯"},
    "体育赛事": {"tag": "体育", "color": "#f97316", "group": "运动"},
    "跑步": {"tag": "跑步", "color": "#f97316", "group": "运动"},
    "传统玄学": {"tag": "玄学", "color": "#a1a1aa", "group": "其他"},
    "塔罗占卜": {"tag": "塔罗", "color": "#a1a1aa", "group": "其他"},
    "其他神秘学": {"tag": "神秘学", "color": "#a1a1aa", "group": "其他"},
    "野生动物动物解说科普": {"tag": "动物", "color": "#a1a1aa", "group": "其他"},
    "动物综合二创": {"tag": "动物", "color": "#a1a1aa", "group": "其他"},
    "小宠异宠": {"tag": "宠物", "color": "#a1a1aa", "group": "其他"},
    "买房租房": {"tag": "房产", "color": "#a1a1aa", "group": "其他"},
    "两性知识": {"tag": "两性", "color": "#a1a1aa", "group": "其他"},
    "健康科普": {"tag": "健康", "color": "#a1a1aa", "group": "其他"},
    "街头采访": {"tag": "街访", "color": "#a1a1aa", "group": "其他"},
    "剧情演绎": {"tag": "剧情", "color": "#a1a1aa", "group": "其他"},
    "汽车生活": {"tag": "汽车", "color": "#a1a1aa", "group": "其他"},
}


GROUP_META: dict[str, dict] = {
    "学习": {"icon": "\U0001f4d6", "order": 0},
    "AI": {"icon": "\U0001f916", "order": 1},
    "成长": {"icon": "\U0001f331", "order": 2},
    "技术": {"icon": "\U0001f4bb", "order": 3},
    "游戏": {"icon": "\U0001f3ae", "order": 4},
    "娱乐": {"icon": "\U0001f389", "order": 5},
    "影视": {"icon": "\U0001f3ac", "order": 6},
    "美食": {"icon": "\U0001f35c", "order": 7},
    "穿搭": {"icon": "\U0001f457", "order": 8},
    "生活": {"icon": "\u2615", "order": 9},
    "旅游": {"icon": "\u2708\ufe0f", "order": 10},
    "健身": {"icon": "\U0001f4aa", "order": 11},
    "运动": {"icon": "\u26bd", "order": 12},
    "资讯": {"icon": "\U0001f4f0", "order": 13},
    "其他": {"icon": "\U0001f4cc", "order": 14},
}

DEFAULT_GROUP = "其他"
DEFAULT_COLOR = "#a1a1aa"


def get_group(category_v2: str, parent_category_v2: str = "") -> str:
    if category_v2 in CATEGORY_MAP:
        return CATEGORY_MAP[category_v2]["group"]
    if parent_category_v2 in PARENT_GROUP_MAP:
        return PARENT_GROUP_MAP[parent_category_v2]
    return DEFAULT_GROUP


def get_tag(category_v2: str) -> str:
    if category_v2 in CATEGORY_MAP:
        return CATEGORY_MAP[category_v2]["tag"]
    return category_v2[:8] if len(category_v2) > 8 else category_v2


def get_color(category_v2: str) -> str:
    if category_v2 in CATEGORY_MAP:
        return CATEGORY_MAP[category_v2]["color"]
    return DEFAULT_COLOR


def get_groups() -> list[dict]:
    return sorted(GROUP_META.values(), key=lambda g: g["order"])


def group_stats(db_path: Path) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT category_v2, parent_category_v2, COUNT(*) as cnt "
            "FROM watch_later GROUP BY category_v2 "
            "ORDER BY cnt DESC"
        ).fetchall()

    group_buckets: dict[str, int] = {}
    tag_buckets: dict[str, dict[str, int]] = {}
    for cat, parent, cnt in rows:
        g = get_group(cat, parent or "")
        t = get_tag(cat)
        group_buckets[g] = group_buckets.get(g, 0) + cnt
        if g not in tag_buckets:
            tag_buckets[g] = {}
        tag_buckets[g][t] = tag_buckets[g].get(t, 0) + cnt

    result = []
    seen = set()
    for g_name in GROUP_META:
        if g_name not in group_buckets:
            continue
        tags_sorted = sorted(tag_buckets[g_name].items(), key=lambda x: -x[1])
        result.append({
            "group": g_name,
            "icon": GROUP_META[g_name]["icon"],
            "count": group_buckets[g_name],
            "subtags": [{"tag": t, "count": c} for t, c in tags_sorted],
        })
        seen.add(g_name)

    for g_name in sorted(group_buckets.keys()):
        if g_name not in seen:
            icon = GROUP_META.get(g_name, {}).get("icon", "\U0001f4cc")
            tags_sorted = sorted(tag_buckets[g_name].items(), key=lambda x: -x[1])
            result.append({
                "group": g_name,
                "icon": icon,
                "count": group_buckets[g_name],
                "subtags": [{"tag": t, "count": c} for t, c in tags_sorted],
            })

    return result
