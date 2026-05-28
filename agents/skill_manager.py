# -*- coding: utf-8 -*-
# @Time    : 2026/5/19 21:04
# @Author  : Zery
# @File    : skill_manager.py
# @Software: PyCharm
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

import yaml
from utils.logger import logger


# 负责管理技能（Skill），从指定目录加载技能信息，并提供访问接口。
@dataclass
class Skill:
    name: str
    description: str
    path: Path
    content: Optional[str] = None
    metadata: Optional[Dict] = None

    def load_full_content(self) -> Optional[str]:
        if self.content is None:
            skill_file = self.path / "SKILL.md"
            self.content = skill_file.read_text(encoding="utf-8")
        return self.content


# 技能管理器，负责从指定目录加载技能信息，并提供访问接口。
class SkillManager:
    def __init__(self, skills_directory: str = "./skills"):
        self.skills_directory = Path(skills_directory)
        self.skills: Dict[str, Skill] = {}
        self.discover_skills()

    # 从技能目录加载技能信息，解析 SKILL.md 文件，并将技能信息存储在 self.skills 字典中。
    def discover_skills(self) -> None:
        if not self.skills_directory.exists():
            logger.warning(f"技能目录不存在: {self.skills_directory}")
            return

        for item in sorted(self.skills_directory.iterdir(), key=lambda path: path.name):
            logger.info(f"发现技能目录: {item}")
            if item.is_dir():
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    skill = self.parse_skill(skill_file, item)
                    self.skills[skill.name] = skill

    # 重新扫描技能目录，适合新增或修改 SKILL.md 后调用。
    def reload(self) -> None:
        self.skills.clear()
        self.discover_skills()

    # 解析 SKILL.md 文件，提取技能的名称、描述和内容，并返回一个 Skill 对象。
    def parse_skill(self, skill_file: Path, skill_dir: Path) -> Skill:
        content = skill_file.read_text(encoding="utf-8")
        metadata = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    content = parts[2].strip()
                except yaml.YAMLError as e:
                    logger.warning(f"无法解析 YAML frontmatter {skill_file}: {e}")
        name = metadata.get("name", skill_dir.name)
        description = metadata.get("description", "No description available")

        return Skill(
            name=name,
            description=description,
            path=skill_dir,
            content=content,
            metadata=metadata,
        )

    # 看到所有的能力列表
    def list_skills(self) -> List[Dict[str, str]]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
            }
            for skill in self.skills.values()
        ]

    # 激活指定的技能，返回技能的完整内容。
    def activate_skill(self, skill_name: str) -> Optional[str]:
        skill = self.skills.get(skill_name)
        if skill:
            return skill.load_full_content()
        else:
            logger.warning(f"技能 {skill_name} 未找到。")
            return None

    # 选择技能，根据用户输入的问题，自动选择最合适的技能，并返回技能名称。
    def select_skill(self) -> str:
        """
        根据用户问题自动选择 skill
        """
        skill_list = self.list_skills()

        skills_text = "\n".join([
            f"- {skill['name']}: {skill['description']}"
            for skill in skill_list
        ])
        return skills_text


if __name__ == '__main__':
    manager = SkillManager("/Users/tom/Desktop/项目/B_S/skills")
    logger.info(manager.select_skill())
