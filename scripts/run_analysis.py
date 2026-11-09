"""Run the preserved analysis from exported CSVs without Colab or Earth Engine.

Only configuration assignments and the unused Earth Engine import are adapted.
The scientific functions and analysis block are executed unchanged.
"""
import argparse
import ast
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=Path(__file__).parent/'analysis.py')
    args = parser.parse_args()
    inputs, output = args.inputs.resolve(), args.output.resolve()
    if output == inputs or output in inputs.parents:
        parser.error('Use a separate output directory.')
    replacements = {
        'PROJECT_DIR': str(inputs)+'/', 'EXPORT_DIR': str(inputs/'gee_exports'),
        'SOURCE_DIR': str(inputs/'source_data'), 'ANALYSIS_DIR': str(output),
        'FIGURES_DIR': str(output/'figures'), 'MOUNT_DRIVE': False,
        'RUN_GEE_EXPORTS': False, 'RUN_CANAL_EXPORT_ONLY': False,
        'RUN_ANALYSIS': True, 'RUN_PLOTS': False,
        'PREPARE_WHEAT_FROM_KAGGLE': False,
    }
    tree = ast.parse(args.source.read_text(encoding='utf-8'))
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and len(statement.targets)==1:
            target = statement.targets[0]
            if isinstance(target, ast.Name) and target.id in replacements:
                statement.value = ast.Constant(replacements[target.id])
    tree.body = [s for s in tree.body if not (isinstance(s, ast.Import) and len(s.names)==1 and s.names[0].name=='ee')]
    ast.fix_missing_locations(tree)
    exec(compile(tree, str(args.source), 'exec'), {'__name__':'__preserved_analysis__'})

if __name__ == '__main__':
    main()
