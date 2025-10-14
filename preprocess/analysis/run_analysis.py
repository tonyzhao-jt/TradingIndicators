import argparse
from pathlib import Path
import json
from category import analyze_file
try:
    import matplotlib.pyplot as plt
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', required=True)
    parser.add_argument('--out-json', '-j', default='analysis_summary.json')
    parser.add_argument('--out-png', '-p', default='analysis_pie.png')
    args = parser.parse_args()

    res = analyze_file(args.input, out_json=args.out_json)

    # create pie chart for type distribution (if matplotlib available)
    summary = res['summary']
    labels = ['indicator', 'strategy', 'unknown']
    sizes = [summary.get('indicator', 0), summary.get('strategy', 0), summary.get('unknown', 0)]

    if _HAS_PLT:
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
        ax.axis('equal')
        plt.title('Script Types Distribution')
        plt.savefig(args.out_png)
        print('Wrote JSON:', args.out_json)
        print('Wrote PNG:', args.out_png)
    else:
        print('matplotlib not available; wrote JSON only.')
        print('Wrote JSON:', args.out_json)


if __name__ == '__main__':
    main()
