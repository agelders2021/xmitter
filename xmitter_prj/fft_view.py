import runpy, os, sys
_tools = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tools'))
if _tools not in sys.path:
    sys.path.insert(0, _tools)
runpy.run_path(os.path.join(_tools, 'fft_view.py'), run_name='__main__')
