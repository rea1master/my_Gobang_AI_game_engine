import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import LEVELS
for k, v in LEVELS.items():
    print(f"{v['name']:>4}: depth={v['depth']:2d} time={v['time']}s "
          f"vcf={v['vcf']} vct={v['vct']} defend={v['defense']} "
          f"blunder={v['blunder']} counter_vct={v.get('counter_vct', False)}")
