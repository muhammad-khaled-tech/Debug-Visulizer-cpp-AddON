# 🚀 Enhanced Debug Visualizer

<div align="center">

**Enhanced C++ Data Structure Visualization for VS Code**

[![Version](https://img.shields.io/badge/version-1.0.0-blue?style=for-the-badge)](https://github.com/muhammad-khaled-tech/Debug-Visulizer-cpp-AddON/releases)
[![VS Code](https://img.shields.io/badge/VS%20Code-Extension-007ACC?style=for-the-badge&logo=visual-studio-code)](https://code.visualstudio.com)
[![License](https://img.shields.io/badge/license-GPL--3.0-orange?style=for-the-badge)](LICENSE.md)

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Examples](#-examples)

</div>

---

## ✨ What Makes This Special?

This is an **enhanced fork** of the popular Debug Visualizer extension, supercharged with:

- 🎨 **Beautiful SVG visualizations** for arrays, linked lists, and trees
- 🎬 **Swap animations** for sorting algorithms (bubble sort, quicksort, etc.)
- 📊 **Stack & Queue** visualizations with push/pop animations
- 🎯 **Color-coded pointers** (i=orange, j=purple, left=green, right=red)
- 📹 **GIF recording** - export your debugging sessions!
- ⚡ **Zero setup** - works in ANY C++ project automatically!

---

## 📥 Installation

### Option 1: Download from Releases (Recommended)
1. Go to [Releases](https://github.com/muhammad-khaled-tech/Debug-Visulizer-cpp-AddON/releases)
2. Download `enhanced-debug-visualizer.vsix`
3. In VS Code: `Extensions` → `...` menu → `Install from VSIX`
4. Select the downloaded file

### Option 2: One-liner
```bash
git clone https://github.com/muhammad-khaled-tech/Debug-Visulizer-cpp-AddON.git
code --install-extension Debug-Visulizer-cpp-AddON/dist/extension.vsix
```

### Python Dependencies (Optional - for GIF export)
```bash
pip install cairosvg pillow
```

---

## 🎯 Usage

1. **Open any C++ project** - No `.vscode` folder needed!
2. **Start debugging** with GDB (press `F5`)
3. **Open visualizer**: `Ctrl+Shift+P` → `Debug Visualizer: New View`
4. **Type your variable name**: `arr`, `head`, `root`, etc.

### Supported Data Structures

| Type | What to Type | Visualization |
|------|--------------|---------------|
| Array | `arr` | SVG boxes with values |
| Vector | `vec` | SVG container |
| Linked List | `head` | Graph with arrows |
| Binary Tree | `root` | Tree layout |
| Stack | `stack` (with `top` variable) | Vertical boxes |
| Queue | `queue` (with `front`/`rear`) | Horizontal boxes |

---

## 🎨 Pointer Color Legend

When visualizing sorting algorithms, pointers are color-coded:

| Variable | Color | Use Case |
|:--------:|:-----:|:---------|
| `i` | 🟠 Orange | Outer loop |
| `j` | 🟣 Purple | Inner loop |
| `left` | 🟢 Green | Left boundary |
| `right` | 🔴 Red | Right boundary |
| `mid` | 🟡 Yellow | Binary search |
| `pivot` | 🩷 Pink | QuickSort |

---

## 📸 Examples

### Bubble Sort with Swap Animation
```cpp
int arr[7] = {64, 34, 25, 12, 22, 11, 90};
for (int i = 0; i < n-1; i++) {
    for (int j = 0; j < n-i-1; j++) {
        if (arr[j] > arr[j+1]) {
            swap(arr[j], arr[j+1]);
            // Visualizer shows animated swap!
        }
    }
}
// Type "arr" in Debug Visualizer - see i, j pointers move!
```

### Two-Pointer Technique
```cpp
Node* slow = head;
Node* fast = head;
while (fast && fast->next) {
    slow = slow->next;
    fast = fast->next->next;
}
// Type "head" - see both pointers highlighted!
```

---

## 🎬 GIF Recording

Record your debugging session as an animated GIF!

```
# In GDB Debug Console:
gif_start bubble_sort    # Start recording
gif_frame arr            # Capture frame (repeat while stepping)
gif_stop                 # Save to exports/bubble_sort.gif
```

---

## 🔧 GDB Commands

| Command | Description |
|---------|-------------|
| `vis <expr>` | Visualize any data structure |
| `vis_arr <arr> <size>` | Visualize C array |
| `vis_vec <vector>` | Visualize std::vector |
| `gif_start <name>` | Start GIF recording |
| `gif_frame <expr>` | Capture frame |
| `gif_stop` | Save GIF |

---

## 🤝 Credits

- Fork of [hediet/vscode-debug-visualizer](https://github.com/hediet/vscode-debug-visualizer)
- Enhanced for **ITI Open Source Applications Development**
- Created by **Mohamed Khaled-ITI**

---

## 📄 License

GPL-3.0 License - See [LICENSE.md](LICENSE.md)

---

<div align="center">

**Made with ❤️ for C++ developers and DSA learners**

⭐ Star this repo if you find it useful!

</div>
