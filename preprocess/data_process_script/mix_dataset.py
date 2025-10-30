#!/usr/bin/env python3
"""
Mix Dataset - 混合 script 和 segment 数据集

按照指定比例混合两个数据集，用于创建多样化的训练数据。
采样策略：不放回采样，持续采样 script 数据直到全部采样完成。
"""

import json
import argparse
import random
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatasetMixer:
    """数据集混合器"""
    
    def __init__(self, script_path, segment_path, script_ratio=0.5, shuffle=True, seed=42):
        """
        初始化混合器
        
        Args:
            script_path: script 数据集路径
            segment_path: segment 数据集路径
            script_ratio: script 数据占比 (0.0-1.0)，默认 0.5 表示 50% script, 50% segment
            shuffle: 是否打乱最终数据集
            seed: 随机种子
        """
        self.script_path = script_path
        self.segment_path = segment_path
        self.script_ratio = max(0.0, min(1.0, script_ratio))  # 限制在 0-1 之间
        self.shuffle = shuffle
        self.seed = seed
        
        random.seed(seed)
        
    def load_data(self, path):
        """加载 JSON 数据"""
        logger.info(f"Loading data from: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} items")
        return data
    
    def validate_format(self, data, source_name):
        """验证数据格式"""
        if not isinstance(data, list):
            raise ValueError(f"{source_name} data must be a list")
        
        if len(data) == 0:
            raise ValueError(f"{source_name} data is empty")
        
        # 检查每个样本是否有 input 和 output 字段
        for idx, item in enumerate(data[:5]):  # 检查前5个样本
            if not isinstance(item, dict):
                raise ValueError(f"{source_name} item {idx} is not a dict")
            if 'input' not in item or 'output' not in item:
                raise ValueError(f"{source_name} item {idx} missing 'input' or 'output' field")
        
        logger.info(f"{source_name} format validated successfully")
    
    def mix_datasets(self):
        """
        混合数据集
        
        策略：
        1. 根据 script_ratio 计算需要多少 script 和 segment 样本
        2. 不放回采样 script 数据
        3. 如果 script 数据不足，从 segment 数据中补充
        4. 持续采样直到所有 script 数据都被使用
        
        Returns:
            mixed_data: 混合后的数据列表
            stats: 统计信息字典
        """
        # 加载数据
        script_data = self.load_data(self.script_path)
        segment_data = self.load_data(self.segment_path)
        
        # 验证格式
        self.validate_format(script_data, "Script")
        self.validate_format(segment_data, "Segment")
        
        # 计算目标数量
        script_count = len(script_data)
        
        # 根据比例计算需要的 segment 数量
        # 如果 script_ratio = 0.5，意味着 50% script, 50% segment
        # 所以 segment_count = script_count (1:1 比例)
        # 如果 script_ratio = 0.3，意味着 30% script, 70% segment
        # 所以 segment_count = script_count * (0.7/0.3) = script_count * 2.33
        
        if self.script_ratio >= 1.0:
            # 100% script，不需要 segment
            segment_count = 0
        elif self.script_ratio <= 0.0:
            # 0% script，全部 segment
            segment_count = len(segment_data)
            script_count = 0
        else:
            # 根据比例计算
            segment_count = int(script_count * (1 - self.script_ratio) / self.script_ratio)
        
        logger.info(f"Target distribution:")
        logger.info(f"  Script samples: {script_count} ({self.script_ratio*100:.1f}%)")
        logger.info(f"  Segment samples: {segment_count} ({(1-self.script_ratio)*100:.1f}%)")
        logger.info(f"  Total: {script_count + segment_count}")
        
        # 采样（不放回）
        # Script: 使用全部数据
        sampled_script = script_data.copy()
        
        # Segment: 随机采样指定数量
        if segment_count >= len(segment_data):
            logger.warning(f"Requested {segment_count} segment samples but only {len(segment_data)} available")
            segment_count = len(segment_data)
        
        sampled_segment = random.sample(segment_data, segment_count) if segment_count > 0 else []
        
        logger.info(f"Actual sampling:")
        logger.info(f"  Script: {len(sampled_script)} samples")
        logger.info(f"  Segment: {len(sampled_segment)} samples")
        
        # 添加来源标记
        for item in sampled_script:
            item['_source'] = 'script'
        
        for item in sampled_segment:
            item['_source'] = 'segment'
        
        # 合并数据
        mixed_data = sampled_script + sampled_segment
        
        # 打乱
        if self.shuffle:
            random.shuffle(mixed_data)
            logger.info("Dataset shuffled")
        
        # 统计信息
        stats = {
            "total_samples": len(mixed_data),
            "script_samples": len(sampled_script),
            "segment_samples": len(sampled_segment),
            "script_ratio": len(sampled_script) / len(mixed_data) if len(mixed_data) > 0 else 0,
            "segment_ratio": len(sampled_segment) / len(mixed_data) if len(mixed_data) > 0 else 0,
            "target_script_ratio": self.script_ratio,
            "shuffle": self.shuffle,
            "seed": self.seed,
            "source_files": {
                "script": str(self.script_path),
                "segment": str(self.segment_path)
            },
            "source_counts": {
                "script_total": len(script_data),
                "segment_total": len(segment_data)
            }
        }
        
        return mixed_data, stats
    
    def save_mixed_dataset(self, mixed_data, stats, output_dir="./outputs"):
        """
        保存混合后的数据集
        
        Args:
            mixed_data: 混合后的数据
            stats: 统计信息
            output_dir: 输出目录
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存混合数据（不包含 _source 标记）
        output_file = Path(output_dir) / f"mixed_dataset_{timestamp}.json"
        clean_data = []
        for item in mixed_data:
            clean_item = {k: v for k, v in item.items() if k != '_source'}
            clean_data.append(clean_item)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Mixed dataset saved to: {output_file}")
        
        # 保存元数据（包含 _source 统计）
        metadata_file = Path(output_dir) / f"mixed_dataset_{timestamp}_metadata.json"
        
        # 添加源分布统计
        source_distribution = {}
        for item in mixed_data:
            source = item.get('_source', 'unknown')
            source_distribution[source] = source_distribution.get(source, 0) + 1
        
        stats['source_distribution'] = source_distribution
        stats['timestamp'] = timestamp
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Metadata saved to: {metadata_file}")
        
        return output_file, metadata_file


def main():
    parser = argparse.ArgumentParser(
        description='Mix script and segment datasets with specified ratio',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mix with 50% script and 50% segment (default)
  python mix_dataset.py --script script_20251030.json --segment segment_20251030.json
  
  # Mix with 30% script and 70% segment
  python mix_dataset.py --script script_20251030.json --segment segment_20251030.json --ratio 0.3
  
  # Mix with 80% script and 20% segment, no shuffle
  python mix_dataset.py --script script_20251030.json --segment segment_20251030.json --ratio 0.8 --no-shuffle
  
  # Specify output directory
  python mix_dataset.py --script script_20251030.json --segment segment_20251030.json --output ./my_datasets
        """
    )
    
    parser.add_argument('--script', '-s', type=str, required=True,
                        help='Path to script dataset JSON file')
    parser.add_argument('--segment', '-g', type=str, required=True,
                        help='Path to segment dataset JSON file')
    parser.add_argument('--ratio', '-r', type=float, default=0.5,
                        help='Script data ratio (0.0-1.0). Default: 0.5 (50%% script, 50%% segment)')
    parser.add_argument('--output', '-o', type=str, default='./outputs',
                        help='Output directory for mixed dataset. Default: ./outputs')
    parser.add_argument('--no-shuffle', action='store_true',
                        help='Do not shuffle the mixed dataset')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility. Default: 42')
    
    args = parser.parse_args()
    
    # 验证输入文件存在
    script_path = Path(args.script)
    segment_path = Path(args.segment)
    
    if not script_path.exists():
        logger.error(f"Script file not found: {script_path}")
        return 1
    
    if not segment_path.exists():
        logger.error(f"Segment file not found: {segment_path}")
        return 1
    
    # 验证比例
    if not 0.0 <= args.ratio <= 1.0:
        logger.error(f"Ratio must be between 0.0 and 1.0, got: {args.ratio}")
        return 1
    
    logger.info("=" * 80)
    logger.info("Dataset Mixer - Starting")
    logger.info("=" * 80)
    logger.info(f"Script dataset: {script_path}")
    logger.info(f"Segment dataset: {segment_path}")
    logger.info(f"Script ratio: {args.ratio:.1%}")
    logger.info(f"Segment ratio: {1-args.ratio:.1%}")
    logger.info(f"Shuffle: {not args.no_shuffle}")
    logger.info(f"Random seed: {args.seed}")
    logger.info(f"Output directory: {args.output}")
    logger.info("=" * 80)
    
    try:
        # 创建混合器
        mixer = DatasetMixer(
            script_path=script_path,
            segment_path=segment_path,
            script_ratio=args.ratio,
            shuffle=not args.no_shuffle,
            seed=args.seed
        )
        
        # 混合数据集
        logger.info("\nMixing datasets...")
        mixed_data, stats = mixer.mix_datasets()
        
        # 保存结果
        logger.info("\nSaving mixed dataset...")
        output_file, metadata_file = mixer.save_mixed_dataset(
            mixed_data, stats, args.output
        )
        
        # 打印总结
        logger.info("\n" + "=" * 80)
        logger.info("Mixing Summary")
        logger.info("=" * 80)
        logger.info(f"Total samples: {stats['total_samples']}")
        logger.info(f"Script samples: {stats['script_samples']} ({stats['script_ratio']:.1%})")
        logger.info(f"Segment samples: {stats['segment_samples']} ({stats['segment_ratio']:.1%})")
        logger.info(f"Output file: {output_file}")
        logger.info(f"Metadata file: {metadata_file}")
        logger.info("=" * 80)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during mixing: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())
