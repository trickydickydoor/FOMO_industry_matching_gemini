import sys
import os
from pathlib import Path

# 添加src目录到路径
current_dir = Path(__file__).parent
src_dir = current_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from industry_matcher import IndustryMatcher

matcher = IndustryMatcher()
matcher.run(limit=10)