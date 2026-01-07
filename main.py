import sys


import visu

if __name__ == "__main__":
    if len(sys.argv) < 2:
        import tkinter.filedialog as fd

        file = fd.askopenfilename(filetypes=[("CGMES files", "*.zip")])
    else:
        file = sys.argv[1]

    visu.run(file)
