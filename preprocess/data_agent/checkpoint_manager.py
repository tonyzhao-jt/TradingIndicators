"""Checkpoint management utilities."""
import json
import sys
from pathlib import Path
from datetime import datetime


class CheckpointManager:
    """Manage processing checkpoints."""
    
    def __init__(self, checkpoint_file: str = "../../outputs/processed/processing_checkpoint.json"):
        """Initialize checkpoint manager."""
        self.checkpoint_file = Path(checkpoint_file)
    
    def show(self):
        """Display current checkpoint status."""
        if not self.checkpoint_file.exists():
            print("No checkpoint found.")
            return
        
        with open(self.checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
        
        print("="*70)
        print("Current Checkpoint Status")
        print("="*70)
        print(f"Last Processed Index: {checkpoint.get('last_processed_index', -1)}")
        print(f"Total Processed: {checkpoint.get('processed_count', 0)}")
        print(f"Total Rejected: {checkpoint.get('rejected_count', 0)}")
        
        if checkpoint.get('processed_count', 0) > 0:
            success_rate = (checkpoint['processed_count'] - checkpoint['rejected_count']) / checkpoint['processed_count'] * 100
            print(f"Success Rate: {success_rate:.2f}%")
        
        if checkpoint.get('timestamp'):
            timestamp = datetime.fromisoformat(checkpoint['timestamp'])
            print(f"Last Updated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("="*70)
    
    def reset(self):
        """Reset checkpoint to start fresh."""
        if not self.checkpoint_file.exists():
            print("No checkpoint to reset.")
            return
        
        # Backup existing checkpoint
        backup_file = self.checkpoint_file.with_suffix('.json.bak')
        import shutil
        shutil.copy(self.checkpoint_file, backup_file)
        print(f"Backed up checkpoint to: {backup_file}")
        
        # Reset checkpoint
        with open(self.checkpoint_file, 'w') as f:
            json.dump({
                "last_processed_index": -1,
                "processed_count": 0,
                "rejected_count": 0,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        
        print("Checkpoint reset successfully.")
    
    def set_index(self, index: int):
        """Set checkpoint to specific index."""
        if not self.checkpoint_file.exists():
            print("No checkpoint found. Creating new checkpoint.")
            checkpoint = {
                "last_processed_index": -1,
                "processed_count": 0,
                "rejected_count": 0,
                "timestamp": None
            }
        else:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
        
        checkpoint['last_processed_index'] = index
        checkpoint['timestamp'] = datetime.now().isoformat()
        
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        print(f"Checkpoint set to index: {index}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python checkpoint_manager.py <command> [args]")
        print("\nCommands:")
        print("  show              - Display current checkpoint status")
        print("  reset             - Reset checkpoint to start from beginning")
        print("  set <index>       - Set checkpoint to specific index")
        print("\nExamples:")
        print("  python checkpoint_manager.py show")
        print("  python checkpoint_manager.py reset")
        print("  python checkpoint_manager.py set 100")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    manager = CheckpointManager()
    
    if command == "show":
        manager.show()
    elif command == "reset":
        confirm = input("Are you sure you want to reset the checkpoint? (yes/no): ")
        if confirm.lower() == "yes":
            manager.reset()
        else:
            print("Reset cancelled.")
    elif command == "set":
        if len(sys.argv) < 3:
            print("Error: Please provide an index number")
            sys.exit(1)
        try:
            index = int(sys.argv[2])
            manager.set_index(index)
        except ValueError:
            print("Error: Index must be a number")
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
