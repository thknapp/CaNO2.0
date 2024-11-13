"""--------Import Section---------""" 
# Standard library imports
import base64
import ctypes
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from io import BytesIO
from uuid import uuid4

# Third-party packages
import pytesseract
from bs4 import BeautifulSoup
from PIL import Image
from spellchecker import SpellChecker

# PyQt6 imports
from PyQt6.QtCore import (
     QByteArray, QBuffer, QDateTime, QEvent, QIODevice, QPoint, QRect, QTimer, QUrl, Qt, QSize, 
     pyqtSignal
)
from PyQt6.QtGui import (
    QAction, QActionGroup, QColor, QFont, QGuiApplication, QIcon, QPainter, QPen, QPixmap,
    QBitmap, QTextCharFormat, QTextCursor, QTextDocument, QTextFormat, QTextImageFormat, QTextListFormat
)
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFontComboBox, QHBoxLayout, QLabel, 
    QLineEdit, QListWidget, QInputDialog, QMainWindow, QMessageBox, QPushButton, QSizePolicy, QSplitter, QSplitterHandle,  
    QTabWidget, QTextEdit, QToolBar, QVBoxLayout, QWidget, QWidgetAction, QMenu, 
)

"""----------Constants for Application Configuration----------"""
APP_NAME = "Case and Note Organizer 2.0"
SCRIPT_NAME = "CaNO2.0"
SETTINGS_DIR = os.path.join(os.getenv('APPDATA'), SCRIPT_NAME)
os.makedirs(SETTINGS_DIR, exist_ok=True)
SETTINGS_FILE = os.path.join(SETTINGS_DIR, f"{SCRIPT_NAME}-settings.json")
CUSTOM_DICT_PATH = os.path.join(SETTINGS_DIR, "custom_dictionary.json")

# Define the folder for persistent storage of saved files
PERSISTENT_FOLDER = os.path.join(SETTINGS_DIR, "saved_files")
os.makedirs(PERSISTENT_FOLDER, exist_ok=True)  # Create the directory if it doesn't exist

# Paths for logging and images
LOG_FILE = os.path.join(os.path.dirname(__file__), f"{SCRIPT_NAME}.log")
IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'images')

# Default Application Settings
DEFAULT_FONT_FAMILY = "Cambria"
DEFAULT_FONT_SIZE = 14
DEFAULT_THEME = "Light Theme"
DEFAULT_WINDOW_SIZE = [800, 600]  # [width, height]
DEFAULT_WINDOW_POSITION = [100, 100]  # [x, y]
FONT_SIZES = [str(i) for i in range(8, 98, 2)]  # Font sizes from 8 to 96 in increments of 2

# Path for storing file metadata JSON
METADATA_FILE = os.path.join(PERSISTENT_FOLDER, "file_metadata.json")

"""----------Toggle Button Styling----------"""
TOGGLE_SWITCH_STYLE = """
    QPushButton {
        background-color: #ccc;
        border: 1px solid #888;
        border-radius: 15px;
        padding: 2px;
        min-width: 40px;
        min-height: 20px;
        color: transparent;  /* Hides any text */
    }
    QPushButton:checked {
        background-color: #4CAF50; /* Green background for "on" state */
        border: 1px solid #3E8E41;
    }
    QPushButton:checked::before {
        content: "ON";
        color: white;
        position: absolute;
        left: 5px;
    }
    QPushButton::before {
        content: "OFF";
        color: black;
        position: absolute;
        right: 5px;
    }
"""

"""----------Button Style for Toggled Format Buttons----------"""
TOGGLED_BUTTON_STYLE = """
    QToolButton:checked {
        background-color: #4CAF50;
        border: 2px solid #3E8E41;
        color: white;
    }
"""

"""----------Logging Setup----------"""
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

"""----------Load JSON Settings----------"""   
# Load settings
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f) or {}
                # Ensure "Auto Save" setting is present with a default value if missing
                settings.setdefault("auto_save", False)  # Default to disabled
                return settings
        except json.JSONDecodeError:
            logger.warning("Settings file is empty or invalid. Using default settings.")
            return {"auto_save": False}  # Default to disabled if file is invalid
    return {"auto_save": False}  # Default if file doesn't exist 
    
def load_file_metadata():
    """Load file metadata from the metadata file or return an empty dictionary if not found."""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_file_metadata(metadata):
    """Save metadata dictionary to JSON file."""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=4)

def update_file_metadata(self, file_name, user_path, persistent_path):
    """Update the metadata with both the user-chosen path and persistent app path."""
    self.metadata[file_name] = {
        "user_path": user_path,
        "persistent_path": persistent_path,
        "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "created_at": self.metadata.get(file_name, {}).get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    }
    self.save_metadata()

# Define the path to the themes file
THEMES_FILE = os.path.join(os.path.dirname(__file__), 'themes.json')

# Load themes from JSON file
def load_themes():
    with open(THEMES_FILE, 'r', encoding='utf-8') as f:
        themes = json.load(f)
    # Convert color and font settings to the expected PyQt objects
    for theme_name, settings in themes.items():
        settings['text_color'] = QColor(settings['text_color'])
        settings['font_family'] = settings.get('font_family', 'Cambria')
        settings['font_size'] = settings.get('font_size', 14)
    return themes

# Load themes
THEMES = load_themes()


"""----------Save Settings----------"""
def save_settings(settings):
    """Save settings to a JSON file, including the 'Auto Save' setting."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)
    logger.info("Settings saved.")

# Load existing settings into a global variable
app_settings = load_settings()  # This should work without issues now


# Highlight Colors
HIGHLIGHT_STYLES = {
    "Light Yellow / Dark Gray": {"highlight": QColor(255, 255, 204), "font": QColor(64, 64, 64)},
    "Light Blue / Dark Navy": {"highlight": QColor(204, 229, 255), "font": QColor(0, 0, 51)},
    "Light Green / Dark Green": {"highlight": QColor(204, 255, 204), "font": QColor(0, 51, 0)},
    "Light Pink / Dark Purple": {"highlight": QColor(255, 204, 229), "font": QColor(51, 0, 51)},
    "Light Orange / Dark Brown": {"highlight": QColor(255, 229, 204), "font": QColor(102, 51, 0)},
    "Light Gray / Black": {"highlight": QColor(224, 224, 224), "font": QColor(0, 0, 0)},
    "Light Purple / Dark Purple": {"highlight": QColor(229, 204, 255), "font": QColor(51, 0, 51)},
    "Light Peach / Dark Brown": {"highlight": QColor(255, 229, 204), "font": QColor(102, 51, 0)},
    "Light Teal / Dark Teal": {"highlight": QColor(204, 255, 255), "font": QColor(0, 51, 51)},
    "Pale Yellow / Dark Olive": {"highlight": QColor(255, 255, 153), "font": QColor(51, 51, 0)},
    "Mint Green / Dark Green": {"highlight": QColor(204, 255, 229), "font": QColor(0, 51, 0)}
}

"""----------Spell Checker Intialization----------""" 
# Spell Checker Initialization
spell = SpellChecker()
if os.path.exists(CUSTOM_DICT_PATH):
    with open(CUSTOM_DICT_PATH, 'r') as f:
        custom_words = json.load(f)
else:
    custom_words = []

# Add custom words to spell checker
spell.word_frequency.load_words(custom_words)

"""----------Function to Minimize the Console Window----------""" 
"""def minimize_console():
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd != 0:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

# Relaunch script minimized if not already minimized
def relaunch_minimized():
    if sys.platform == "win32" and "--minimized" not in sys.argv:
        subprocess.Popen(["python", __file__, "--minimized"], creationflags=win32con.SW_HIDE)
        sys.exit()

# Relaunch if not minimized
if "--minimized" not in sys.argv:
    relaunch_minimized()
else:
    sys.argv.remove("--minimized")
    minimize_console()  # Minimize console window after relaunch"""
    
"""==========Main Window Class=========="""
# Main window class initialization and UI setup
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Case and Note Organizer 2.0")
        
        # Initialize thumbnail image map to store thumbnail images
        self.thumbnail_image_map = {} 
        
        # Initialize full_image_map in MainWindow
        self.full_image_map = {} 
        
        self.editor = ClickableTextEdit(self)
        self.editor.full_image_map = self.full_image_map 
        
        # Path to the icon in the images folder
        icon_path = os.path.join(os.path.dirname(__file__), "images", "cano.ico")
        if not os.path.exists(icon_path):
            print("Icon file not found at:", icon_path)

        # Set the window icon specifically for the main window
        self.setWindowIcon(QIcon(icon_path))
       
        # Initialize essential attributes
        self.capture_in_progress = False  # Tracks if a capture is in progress
        self.full_image_map = {}  # Stores full-size images by URL
        self.capture_area_set = False  # Flag to track if capture area has been set
        self.current_highlight_color = list(HIGHLIGHT_STYLES.values())[0]  # Default to the first color
        self.images_dir = os.path.join(os.path.dirname(__file__), 'images')  # Path to icons

        # Load settings for theme and font
        self.current_theme = app_settings.get("theme", DEFAULT_THEME)
        self.current_theme_settings = THEMES.get(self.current_theme, THEMES["Light Theme"])
        self.current_font_family = app_settings.get("font_family", DEFAULT_FONT_FAMILY)
        self.current_font_size = app_settings.get("font_size", DEFAULT_FONT_SIZE)
        self.auto_save_enabled = app_settings.get("auto_save", False) 
   
        # Set window size and position from settings
        window_size = app_settings.get("window_size", DEFAULT_WINDOW_SIZE)
        window_position = app_settings.get("window_position", DEFAULT_WINDOW_POSITION)
        self.resize(window_size[0], window_size[1])
        self.move(window_position[0], window_position[1])
        
        # Initialize FileMetadataManager
        self.file_metadata_manager = FileMetadataManager()
        
        # Initialize path tracking
        self.paths = {}  # Stores file paths for each tab

        # Set up main tab widget and add a plus button to its tab bar
        self.setup_tab_widget()

        # Initialize UI components
        self.init_ui()  # Setup UI elements like toolbars, menus, etc.      
      
        # Apply global style for toggled buttons and the selected theme
        self.setStyleSheet(TOGGLED_BUTTON_STYLE)    
        self.apply_theme(self.current_theme)

        self.settings_menu.addAction("Edit Custom Dictionary", self.edit_custom_dictionary)

        # Apply default font settings to the editor
        self.apply_default_font_settings()

        # Force a repaint and update to apply all theme and layout settings
        self.repaint()
        self.update()
             
        # Initialize splitter for main layout
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)

        # Use the custom splitter with a handle
        self.splitter = CustomSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)

        # Initialize saved files panel
        self.saved_files_panel = SavedFilesPanel(self)
        self.saved_files_panel.setMaximumWidth(200)
        self.splitter.addWidget(self.saved_files_panel)

        # Initialize editor tab widget and add to layout
        tab_layout = QHBoxLayout()  # Layout to hold the tab widget and the "+" button

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)  # Enable close buttons on tabs
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.splitter.addWidget(self.tab_widget)
        
        # Adding the "+" button to the tab bar directly
        self.new_tab_button = QPushButton("  +  ", self.tab_widget)
        self.new_tab_button.setFixedSize(25, 20)  # Adjust size as needed
        self.new_tab_button.setToolTip("New Tab")
        self.new_tab_button.clicked.connect(self.add_new_tab)

        # Set font size and make it bold
        font = self.new_tab_button.font()
        font.setPointSize(16)  # Set the desired font size
        font.setBold(True)      # Make the font bold
        self.new_tab_button.setFont(font)

        self.new_tab_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
                margin-left: 5px;
            }
            QPushButton:hover {
                background-color: rgba(211, 211, 211, 0.0);  /* Light gray with 30% opacity */
                border-radius: 4px;
            }
            """)
        
        # Add the button to the right end of the tab bar
        self.tab_widget.setCornerWidget(self.new_tab_button, Qt.Corner.TopRightCorner)
        
        # Add the initial tab
        self.add_new_tab()
        
    def setup_custom_context_menu(self):
        """Sets up the custom context menu policy and connects the right-click event."""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_custom_context_menu)

    def sync_toggle_buttons(self):
        """Sync the visibility of the saved files panel with the View menu toggle action."""
        if self.toggle_panel_action.isChecked():
            self.saved_files_panel.show()
           # self.toggle_panel_action.setText("Hide Panel")
            self.saved_files_panel.collapse_button.setText("◀")  # Icon to collapse
        else:
            self.saved_files_panel.hide()
            self.toggle_panel_action.setText("Show Panel")
            self.saved_files_panel.collapse_button.setText("▶")  # Icon to expand

    def toggle_panel_visibility(self):
        """Toggle visibility of the saved files panel and update the button text."""
        if self.toggle_panel_action.isChecked():
            self.saved_files_panel.show()
            self.toggle_panel_action.setText("Hide Panel")
        else:
            self.saved_files_panel.hide()
          #  self.toggle_panel_action.setText("Show Panel")        
        
        logger.info("User interface initialized with tab support.")

    def apply_theme(self, theme_name):
        """Apply the specified theme to the application and save the setting."""
        theme = THEMES.get(theme_name, THEMES["Light Theme"])
        self.setStyleSheet(theme["style"])  # Apply main theme style
        self.current_theme = theme_name
        self.current_theme_settings = theme  # Update current theme settings in memory

        # Apply to individual elements if needed
        self.tab_widget.setStyleSheet(theme["style"])  
        app_settings["theme"] = theme_name  # Save theme to settings
        save_settings(app_settings)  # Persist change
        self.repaint()  # Force a repaint to apply changes
        logger.info(f"Applied and saved theme: {theme_name}")

    def closeEvent(self, event):
        """Override close event to auto-save modified documents without prompt on exit if autosave is enabled."""
        for index in reversed(range(self.tab_widget.count())):
            editor = self.tab_widget.widget(index)
            file_path = self.paths.get(index)

            # Auto-save modified documents before closing the program if autosave is enabled
            if self.autosave_toggle_button.isChecked() and editor.document().isModified():
                if file_path:
                    self.auto_save_current_tab(index=index)
                else:
                    # If no filename, save with default auto-generated name in persistent folder
                    file_name = f"Untitled_{index + 1}.txt"
                    persistent_path = os.path.join(PERSISTENT_FOLDER, file_name)
                    with open(persistent_path, 'w', encoding='utf-8') as f:
                        f.write(editor.toPlainText())
                    self.file_metadata_manager.update_file_metadata(file_name, persistent_path, persistent_path)
                    self.saved_files_panel.add_saved_file(file_name)

            # Remove empty auto-saved files
            if file_path and file_path.startswith(PERSISTENT_FOLDER) and self.is_tab_empty(editor):
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.file_metadata_manager.remove_metadata_entry(os.path.basename(file_path))
                    logger.info(f"Empty auto-saved file removed on exit: {file_path}")
                    self.saved_files_panel.refresh_files_list()

            # Close each tab after auto-save or empty check
            self.close_tab(index)

        # Save window settings and other configurations on exit
        app_settings["window_size"] = [self.size().width(), self.size().height()]
        app_settings["window_position"] = [self.pos().x(), self.pos().y()]
        save_settings(app_settings)
        super().closeEvent(event)

    def setup_tab_widget(self):
        """Set up the main tab widget and assign it as the central widget."""
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_tab_context_menu)
        self.setCentralWidget(self.tab_widget)  # Set the tab widget as the central widget
       
    def close_tab(self, index):
        editor = self.tab_widget.widget(index)
        file_path = self.paths.get(index)

        # Check if the document has unsaved changes
        if editor.document().isModified() and not self.autosave_toggle_button.isChecked():
            # Prompt for saving unsaved changes only if autosave is disabled
            response = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"The document '{self.tab_widget.tabText(index)}' has unsaved changes. Would you like to save them?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )

            if response == QMessageBox.StandardButton.Save:
                self.file_save(index)
            elif response == QMessageBox.StandardButton.Cancel:
                return  # Do not close the tab if canceled
        else:
            # Remove empty auto-saved files (files with no text or images) if autosave is enabled and document is unmodified
            if file_path and file_path.startswith(PERSISTENT_FOLDER) and self.is_tab_empty(editor):
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.file_metadata_manager.remove_metadata_entry(os.path.basename(file_path))
                    logger.info(f"Empty auto-saved file removed: {file_path}")
                    self.saved_files_panel.refresh_files_list()

        # Close the tab
        self.tab_widget.removeTab(index)
        if index in self.paths:
            del self.paths[index]
        logger.info(f"Tab at index {index} closed.")

    def close_all_tabs(self):
        """Close all tabs, prompting for unsaved changes if necessary."""
        for index in reversed(range(self.tab_widget.count())):
            self.tab_widget.setCurrentIndex(index)
            self.close_tab(index)     

    def init_ui(self):
        """Initialize menus, toolbars, and theme settings."""
        menubar = self.menuBar()
        self.file_menu = menubar.addMenu("File")
        self.edit_menu = menubar.addMenu("Edit")
        self.search_menu = menubar.addMenu("Search")
        self.view_menu = menubar.addMenu("View")
        self.format_menu = menubar.addMenu("Format")
        self.font_menu = menubar.addMenu("Font")
        self.settings_menu = menubar.addMenu("Settings")

        # Add Themes menu under Settings
        self.themes_menu = QMenu("Themes", self)
        self.settings_menu.addMenu(self.themes_menu)
        for theme_name in THEMES.keys():
            theme_action = QAction(theme_name, self)
            theme_action.triggered.connect(lambda checked, name=theme_name: self.apply_theme(name))
            self.themes_menu.addAction(theme_action)

        # Add "Toggle Panel" action to the View menu
        self.toggle_panel_action = QAction("Saved Files Panel", self, checkable=True)
        self.toggle_panel_action.setChecked(True)  # Start with the panel visible
        self.toggle_panel_action.triggered.connect(self.sync_toggle_buttons)
        self.view_menu.addAction(self.toggle_panel_action)

        # Initialize toolbars in the correct order
        self.init_auto_save_toolbar()
        self.init_edit_toolbar()
        self.init_font_toolbar()
        
      #  self.addToolBarBreak() 

        self.init_file_toolbar()
        self.init_format_toolbar()
        self.init_spell_check_toolbar()  # Spell check toolbar uses format toolbar
        self.init_align_toolbar()
        self.init_list_toolbar()
        self.init_capture_toolbar()



    """----------------------------------------------------------Toolbars-------------------------------------------------""" 

    """----------Auto Save Toolbar----------"""
    def init_auto_save_toolbar(self):
        """Initialize Auto Save toolbar with a custom toggle switch button and a label above it."""
        toolbar = QToolBar("Auto Save")
        self.addToolBar(toolbar)

        # Create a layout to hold both the label and button
        layout = QVBoxLayout()

        # Create the label and add it to the layout
        autosave_label = QLabel("Auto Save")  # Text to appear above the button
        autosave_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center-align text
        layout.addWidget(autosave_label)

        # Create the toggle switch button
        self.autosave_toggle_button = QPushButton("OFF")
        self.autosave_toggle_button.setCheckable(True)
        self.autosave_toggle_button.setFixedSize(60, 30)
        self.autosave_toggle_button.clicked.connect(self.handle_autosave_toggle)

        # Set the initial state and color based on saved settings
        self.autosave_toggle_button.setChecked(self.auto_save_enabled)
        self.update_toggle_style(self.auto_save_enabled)

        # Add the button to the layout and set initial style
        layout.addWidget(self.autosave_toggle_button)
        widget = QWidget()
        widget.setLayout(layout)
        toolbar.addWidget(widget)

    """----------Alignment Toolbar----------"""
    def init_align_toolbar(self):
        """Initialize the alignment toolbar."""
        align_toolbar = QToolBar("Align")
        align_toolbar.setIconSize(QSize(30, 30))
        self.addToolBar(align_toolbar)

        # Left alignment action
        align_left_action = QAction(QIcon(os.path.join(self.images_dir, 'align-left.png')), "Align Left", self)
        align_left_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignLeft))
        align_toolbar.addAction(align_left_action)

        # Center alignment action
        align_center_action = QAction(QIcon(os.path.join(self.images_dir, 'align-center.png')), "Align Center", self)
        align_center_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignCenter))
        align_toolbar.addAction(align_center_action)

        # Right alignment action
        align_right_action = QAction(QIcon(os.path.join(self.images_dir, 'align-right.png')), "Align Right", self)
        align_right_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignRight))
        align_toolbar.addAction(align_right_action)

        # Justify alignment action
        align_justify_action = QAction(QIcon(os.path.join(self.images_dir, 'align-justify.png')), "Align Justify", self)
        align_justify_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignJustify))
        align_toolbar.addAction(align_justify_action)

            
    """----------Capture Toolbar----------"""  
    def init_capture_toolbar(self):
        """Initialize Capture toolbar."""
        self.capture_toolbar = QToolBar("Capture")
        self.capture_toolbar.setIconSize(QSize(30, 30))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.capture_toolbar)

        # Set Capture Area Button
        set_capture_area_action = QAction(QIcon(os.path.join(self.images_dir, 'set_capture.png')), "Set Capture Area", self)
        set_capture_area_action.triggered.connect(self.set_capture_area)
        self.capture_toolbar.addAction(set_capture_area_action)
        
        # Spacer Widget
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.capture_toolbar.addWidget(spacer)

        screen_grab_button = QPushButton(QIcon(os.path.join(self.images_dir, 'screen_grab.png')), "", self)
        screen_grab_button.setIconSize(QSize(45, 45))
        screen_grab_button.clicked.connect(self.screen_grab)
        self.capture_toolbar.addWidget(screen_grab_button)
        
        # OCR Button
        ocr_button = QPushButton(QIcon(os.path.join(self.images_dir, 'ocr.png')), "", self)
        ocr_button.setIconSize(QSize(45, 45))
        ocr_button.clicked.connect(self.perform_ocr)
        self.capture_toolbar.addWidget(ocr_button)  

        capture_button = QPushButton(QIcon(os.path.join(self.images_dir, 'capture.png')), "", self)
        capture_button.setIconSize(QSize(45, 45))
        capture_button.clicked.connect(self.capture)
        self.capture_toolbar.addWidget(capture_button)

    """----------Edit Toolbar----------"""
    def init_edit_toolbar(self):
        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(15, 15))
        self.addToolBar(edit_toolbar)

        # Undo and Redo
        undo_action = QAction(QIcon(os.path.join(self.images_dir, 'arrow-curve_left.png')), "Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(lambda: self.get_current_editor().undo())
        edit_toolbar.addAction(undo_action)
        self.edit_menu.addAction(undo_action)

        redo_action = QAction(QIcon(os.path.join(self.images_dir, 'arrow-curve_right.png')), "Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(lambda: self.get_current_editor().redo())
        edit_toolbar.addAction(redo_action)
        self.edit_menu.addAction(redo_action)

        # Cut, Copy, Paste
        cut_action = QAction(QIcon(os.path.join(self.images_dir, 'scissors.png')), "Cut", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(lambda: self.get_current_editor().cut())
        edit_toolbar.addAction(cut_action)
        self.edit_menu.addAction(cut_action)

        copy_action = QAction(QIcon(os.path.join(self.images_dir, 'document-copy.png')), "Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(lambda: self.get_current_editor().copy())
        edit_toolbar.addAction(copy_action)
        self.edit_menu.addAction(copy_action)

        paste_action = QAction(QIcon(os.path.join(self.images_dir, 'clipboard-paste-document-text.png')), "Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(lambda: self.get_current_editor().paste())
        edit_toolbar.addAction(paste_action)
        self.edit_menu.addAction(paste_action)

    """----------File Toolbar----------"""
    def init_file_toolbar(self):
        """Initialize the file toolbar with Close All Tabs option."""
        toolbar = QToolBar("File")
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        new_window_action = QAction(QIcon(os.path.join(self.images_dir, 'new-instance.png')), "New Instance", self)
        new_window_action.setShortcut("Ctrl+N")
        new_window_action.triggered.connect(self.open_new_instance)
        toolbar.addAction(new_window_action)
        self.file_menu.addAction(new_window_action)

        # New Tab
        new_tab_action = QAction(QIcon(os.path.join(self.images_dir, 'new-tab.png')), "New Tab", self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(self.add_new_tab)
        toolbar.addAction(new_tab_action)
        self.file_menu.addAction(new_tab_action)

        # Open File
        open_action = QAction(QIcon(os.path.join(self.images_dir, 'open_file.png')), "Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.file_open)
        toolbar.addAction(open_action)
        self.file_menu.addAction(open_action)

        # Save File
        save_action = QAction(QIcon(os.path.join(self.images_dir, 'save.png')), "Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(lambda: self.file_save(self.tab_widget.currentIndex()))
        toolbar.addAction(save_action)
        self.file_menu.addAction(save_action)

        # Save As
        saveas_action = QAction(QIcon(os.path.join(self.images_dir, 'save_as.png')), "Save As...", self)
        saveas_action.setShortcut("Ctrl+Alt+S")
        saveas_action.triggered.connect(lambda: self.file_save_as(self.tab_widget.currentIndex()))
        toolbar.addAction(saveas_action)
        self.file_menu.addAction(saveas_action)

        # Close All Tabs
        close_all_action = QAction(QIcon(os.path.join(self.images_dir, 'close-tab.png')), "Close All Tabs", self)
        close_all_action.setShortcut("Ctrl+Shift+W")
        close_all_action.triggered.connect(self.close_all_tabs)
        toolbar.addAction(close_all_action)
        self.file_menu.addAction(close_all_action)

    """----------Font Toolbar----------"""
    def init_font_toolbar(self):
        toolbar = QToolBar("Font")
        toolbar.setIconSize(QSize(10, 10))
        self.addToolBar(toolbar)

        # Font ComboBox
        font_box = QFontComboBox()
        font_box.setCurrentFont(QFont(self.current_font_family))
        font_box.currentFontChanged.connect(self.on_font_change)
        toolbar.addWidget(font_box)

        # Font Size ComboBox
        size_box = QComboBox()
        size_box.addItems(FONT_SIZES)
        size_box.setCurrentText(str(self.current_font_size))
        size_box.currentTextChanged.connect(self.on_fontsize_change)
        size_box.setMinimumWidth(50)
        toolbar.addWidget(size_box)

    """----------Format Toolbar----------"""
    def init_format_toolbar(self):
        """Initialize the format toolbar and assign it to self.format_toolbar."""
        self.format_toolbar = QToolBar("Format")
        self.format_toolbar.setIconSize(QSize(30, 30))
        self.addToolBar(self.format_toolbar)

        # Bold Button
        self.bold_action = QAction(QIcon(os.path.join(self.images_dir, 'bold.png')), "Bold", self)
        self.bold_action.setCheckable(True)
        self.bold_action.setShortcut("Ctrl+B")
        self.bold_action.toggled.connect(lambda checked: self.toggle_text_format("bold", checked))
        self.format_toolbar.addAction(self.bold_action)

        # Apply toggled style for Bold button
        bold_button = self.format_toolbar.widgetForAction(self.bold_action)
        bold_button.setStyleSheet(TOGGLED_BUTTON_STYLE)


        # Italic Button
        self.italic_action = QAction(QIcon(os.path.join(self.images_dir, 'italic.png')), "Italic", self)
        self.italic_action.setCheckable(True)
        self.italic_action.setShortcut("Ctrl+I")
        self.italic_action.toggled.connect(lambda checked: self.toggle_text_format("italic", checked))
        self.format_toolbar.addAction(self.italic_action)

        # Apply toggled style for Italic button
        italic_button = self.format_toolbar.widgetForAction(self.italic_action)
        italic_button.setStyleSheet(TOGGLED_BUTTON_STYLE)

        # Underline Button
        self.underline_action = QAction(QIcon(os.path.join(self.images_dir, 'underline.png')), "Underline", self)
        self.underline_action.setCheckable(True)
        self.underline_action.setShortcut("Ctrl+U")
        self.underline_action.toggled.connect(lambda checked: self.toggle_text_format("underline", checked))
        self.format_toolbar.addAction(self.underline_action)

        # Apply toggled style for Underline button
        underline_button = self.format_toolbar.widgetForAction(self.underline_action)
        underline_button.setStyleSheet(TOGGLED_BUTTON_STYLE)

        # Strikethrough Button
        self.strikethrough_action = QAction(QIcon(os.path.join(self.images_dir, 'strikethrough.png')), "Strikethrough", self)
        self.strikethrough_action.setCheckable(True)
        self.strikethrough_action.toggled.connect(lambda checked: self.toggle_text_format("strikethrough", checked))
        self.format_toolbar.addAction(self.strikethrough_action)

        # Apply toggled style for StrikeThrough button
        strikethrough_button = self.format_toolbar.widgetForAction(self.strikethrough_action)
        strikethrough_button.setStyleSheet(TOGGLED_BUTTON_STYLE)

        # Highlight Button with Dropdown
        self.highlight_action = QAction(QIcon(os.path.join(self.images_dir, 'highlighter.png')), "Highlight", self)
        self.highlight_action.setCheckable(True)
        self.highlight_action.toggled.connect(lambda checked: self.toggle_highlighting(checked))
        self.format_toolbar.addAction(self.highlight_action)

        # Apply toggled style for Highlight button
        highlight_button = self.format_toolbar.widgetForAction(self.highlight_action)
        highlight_button.setStyleSheet(TOGGLED_BUTTON_STYLE)

        # Create a dropdown menu for highlight color selection
        highlight_menu = QMenu("Highlight Colors", self)
        highlight_group = QActionGroup(self)
        highlight_group.setExclusive(True)

        for name, colors in HIGHLIGHT_STYLES.items():
            action = self.create_highlight_action(name, colors)
            action.setCheckable(True)
            action.setData(colors)
            action.triggered.connect(self.on_highlight_color_selected)
            highlight_group.addAction(action)
            highlight_menu.addAction(action)

        # Attach menu to highlight action
        self.highlight_action.setMenu(highlight_menu)
        self.current_highlight_color = list(HIGHLIGHT_STYLES.values())[0]  # Default color

        # Clear Formatting Button
        clear_format_action = QAction(QIcon(os.path.join(self.images_dir, 'clear_format.png')), "Clear Formatting", self)
        clear_format_action.setShortcut("Ctrl+Space")
        clear_format_action.triggered.connect(self.clear_formatting)
        self.format_toolbar.addAction(clear_format_action)

    """----------List Toolbar----------"""
    def init_list_toolbar(self):
        list_toolbar = QToolBar("Lists")
        list_toolbar.setIconSize(QSize(30, 30))
        self.addToolBar(list_toolbar)

        bullet_list_action = QAction(QIcon(os.path.join(self.images_dir, 'bullet.png')), "Bullet List", self)
        bullet_list_action.setShortcut("Ctrl+Shift+L")
        bullet_list_action.triggered.connect(self.add_bullet_list)
        list_toolbar.addAction(bullet_list_action)
        self.format_menu.addAction(bullet_list_action)

        numbered_list_action = QAction(QIcon(os.path.join(self.images_dir, 'numbered-list.png')), "Numbered List", self)
        numbered_list_action.setShortcut("Ctrl+Shift+N")
        numbered_list_action.triggered.connect(self.add_numbered_list)
        list_toolbar.addAction(numbered_list_action)
        self.format_menu.addAction(numbered_list_action)

        increase_indent_action = QAction(QIcon(os.path.join(self.images_dir, 'indent.png')), "Increase Indent", self)
        increase_indent_action.setShortcut("Ctrl+Tab")
        increase_indent_action.triggered.connect(self.increase_indent)
        list_toolbar.addAction(increase_indent_action)

        decrease_indent_action = QAction(QIcon(os.path.join(self.images_dir, 'outdent.png')), "Decrease Indent", self)
        decrease_indent_action.setShortcut("Ctrl+Shift+Tab")
        decrease_indent_action.triggered.connect(self.decrease_indent)
        list_toolbar.addAction(decrease_indent_action)
        
    """----------Spell Check Toolbar-----------"""
    def init_spell_check_toolbar(self):
        """Initialize Spell Check toolbar."""
        toolbar = QToolBar("Spell Check")  # Define the toolbar for spell check
        self.addToolBar(toolbar)

        # Spell Check Toggle Button
        self.spell_check_action = QAction(QIcon(os.path.join(self.images_dir, 'spellcheck.png')), "Spell Check", self)
        self.spell_check_action.setCheckable(True)
        self.spell_check_action.toggled.connect(self.toggle_real_time_spell_check)
        toolbar.addAction(self.spell_check_action)
        
        # Apply toggled style for Spell Check button
        spell_check_button = toolbar.widgetForAction(self.spell_check_action)
        if spell_check_button:
            spell_check_button.setStyleSheet(TOGGLED_BUTTON_STYLE)

        self.spell_check_toolbar = toolbar  # Store the toolbar as an attribute if needed later


    """--------------------------------------------------------Alightment Methods-------------------------------------------""" 
    """----------Alignment Action Methods----------"""
    def set_alignment(self, alignment):
        """Set the alignment for the current text in the editor."""
        editor = self.get_current_editor()
        if editor:
            editor.setAlignment(alignment)
            logger.info(f"Text alignment set to {alignment}.")

    """----------Helper Methods for Alignment----------"""
    def get_current_editor(self):
        """Retrieve the current editor widget."""
        return self.tab_widget.currentWidget()

    def get_current_tab_index(self):
        """Get the current index of the active tab."""
        return self.tab_widget.currentIndex()
        
    """----------------------------------------------------------Auto Save Methods---------------------------------------------"""
    def toggle_autosave(self, checked):
        """Enable or disable autosave based on toggle state."""
        if checked:
            logger.info("Autosave enabled.")
            # Add autosave functionality here
        else:
            logger.info("Autosave disabled.")
            # Disable autosave functionality here

    def handle_autosave_toggle(self):
        """Handle the auto-save toggle and apply style based on state."""
        is_checked = self.autosave_toggle_button.isChecked()
        self.update_toggle_style(is_checked)

        # Enable or disable the auto-save timer based on toggle state
        if is_checked:
            self.enable_auto_save_timer()
        else:
            self.disable_auto_save_timer()

        # Update and save the "auto_save" setting
        app_settings["auto_save"] = is_checked
        save_settings(app_settings)  # Persist the change
        logger.info(f"Auto Save setting updated to: {'enabled' if is_checked else 'disabled'}")

    def toggle_autosave(self, enabled):
        """Enable or disable autosave functionality."""
        print("Autosave enabled" if enabled else "Autosave disabled")

    def update_toggle_style(self, is_checked):
        """Update the style of the toggle button based on its state."""
        if is_checked:
            # Style for "ON" state with green color
            self.autosave_toggle_button.setStyleSheet(
                """
                QPushButton {
                    background-color: #4CAF50;  /* Green for ON */
                    color: white;
                    border-radius: 10px;
                    min-width: 40px;
                    min-height: 20px;
                    font-weight: bold;
                }
                """
            )
            self.autosave_toggle_button.setText("ON")
        else:
            # Style for "OFF" state with gray color
            self.autosave_toggle_button.setStyleSheet(
                """
                QPushButton {
                    background-color: #ccc;  /* Gray for OFF */
                    color: black;
                    border-radius: 10px;
                    min-width: 40px;
                    min-height: 20px;
                    font-weight: bold;
                }
                """
            )
            self.autosave_toggle_button.setText("OFF")

    def enable_auto_save_timer(self):
        """Enable the auto-save timer to periodically save content."""
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_current_tab)
        self.auto_save_timer.start(5000)  # Adjust interval as needed (5000ms = 5 seconds)
        logger.info("Auto-save timer started.")

    def disable_auto_save_timer(self):
        """Disable the auto-save timer."""
        if hasattr(self, 'auto_save_timer'):
            self.auto_save_timer.stop()
            del self.auto_save_timer
        logger.info("Auto-save timer stopped.")

    def auto_save_current_tab(self, index=None):
        """Auto-save the content of the current tab if it has been modified."""
        if index is None:
            index = self.get_current_tab_index()
        
        editor = self.tab_widget.widget(index)
        file_path = self.paths.get(index)

        # Check if the editor is None to avoid accessing an attribute of None
        if editor is not None and editor.document().isModified() and file_path and file_path.startswith(PERSISTENT_FOLDER):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(editor.toPlainText())
            editor.document().setModified(False)  # Reset modified flag after saving
            logger.info(f"Auto-saved changes to: {file_path}")
        else:
            logger.warning("No editor found for the current tab or tab not modified; auto-save skipped.")

    """---------------------------------------------------------Capture Methods----------------------------------------------""" 
    """----------Capture and OCR Action Methods----------"""
    def set_capture_area(self):
        """Launch overlay for setting the capture area, and trigger capture if set."""
        screens = QGuiApplication.screens()
        self.overlays = []

        def close_all_overlays(rect):
            for overlay in self.overlays:
                overlay.close()
            self.on_capture_area_set(rect)

        for screen in screens:
            screen_rect = screen.geometry()
            overlay = SnippingOverlay(screen_rect, close_all_callback=close_all_overlays)
            overlay.showFullScreen()
            overlay.activateWindow()
            overlay.raise_()
            self.overlays.append(overlay)

        logger.info("Snipping tool initialized on all screens.")

    def capture(self):
        """Capture the screen area if set; otherwise prompt user to set the area first."""
        if not self.capture_area_set:
            self.capture_in_progress = True  # Set flag to capture after area is set
            self.set_capture_area()
            return

        pixmap = self.capture_pixmap(self.capture_area)
        if pixmap:
            self.insert_image_with_thumbnail(pixmap)
        else:
            QMessageBox.warning(self, "Capture Failed", "Failed to capture the pre-set area.")

    def perform_ocr(self):
        """Launch OCR overlay for selecting screen area and extracting text from the selected region."""
        screens = QGuiApplication.screens()
        self.overlays = []

        def close_all_overlays(rect):
            for overlay in self.overlays:
                overlay.close()
            self.ocr_from_selected_area(rect)

        for screen in screens:
            screen_rect = screen.geometry()
            overlay = SnippingOverlay(screen_rect, close_all_callback=close_all_overlays)
            overlay.showFullScreen()
            overlay.activateWindow()
            overlay.raise_()
            self.overlays.append(overlay)

        logger.info("OCR overlay initialized.")

    def screen_grab(self):
        """Capture a quick screenshot of a selected screen area and insert it as a thumbnail."""
        screens = QGuiApplication.screens()
        self.overlays = []  # Reset overlays

        def close_all_overlays(rect):
            for overlay in self.overlays:
                overlay.close()
            pixmap = self.capture_pixmap(rect)
            if pixmap:
                self.insert_image_with_thumbnail(pixmap)

        for screen in screens:
            screen_rect = screen.geometry()
            overlay = SnippingOverlay(screen_rect, close_all_callback=close_all_overlays)
            overlay.showFullScreen()
            overlay.activateWindow()
            overlay.raise_()
            self.overlays.append(overlay)

        logger.info("Screen grab overlay initialized.")

    """----------Helper Methods for Capture and OCR----------"""
    def capture_pixmap(self, snip_rect):
        """Capture a pixmap of the specified area within the given screen rectangle."""
        screens = QGuiApplication.screens()
        selected_screen = None
        for screen in screens:
            if screen.geometry().contains(snip_rect.center()):
                selected_screen = screen
                break
        if not selected_screen:
            selected_screen = QGuiApplication.primaryScreen()

        # Adjust capture area coordinates relative to screen
        screen_rect = selected_screen.geometry()
        adjusted_x = snip_rect.x() - screen_rect.x()
        adjusted_y = snip_rect.y() - screen_rect.y()

        # Capture the screenshot within the selected area
        pixmap = selected_screen.grabWindow(0, adjusted_x, adjusted_y, snip_rect.width(), snip_rect.height())
        return pixmap if not pixmap.isNull() else None

    def clear_formatting_near_thumbnail(self):
        """Clear formatting if the cursor is within one space of a thumbnail image."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()

            # Check if the character to the left or right of the cursor is a zero-width space
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
            left_buffer = cursor.selectedText() == '\u200b'
            cursor.clearSelection()

            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            right_buffer = cursor.selectedText() == '\u200b'
            cursor.clearSelection()

            # Clear formatting if the cursor is within one space of a thumbnail
            if left_buffer or right_buffer:
                neutral_format = QTextCharFormat()
                cursor.setCharFormat(neutral_format)
                editor.setTextCursor(cursor)

    def ocr_from_selected_area(self, snip_rect):
        """Capture selected area and perform OCR on it, inserting text into the document."""
        pixmap = self.capture_pixmap(snip_rect)
        if pixmap:
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.ReadWrite)
            pixmap.save(buffer, "PNG")
            buffer.seek(0)

            # Perform OCR with Tesseract
            image_data = BytesIO(buffer.data())
            pil_image = Image.open(image_data)
            ocr_text = pytesseract.image_to_string(pil_image)

            editor = self.get_current_editor()
            if editor and isinstance(editor, QTextEdit):
                cursor = editor.textCursor()
                cursor.insertText(ocr_text)
                logger.info("OCR text inserted into document.")

    def on_capture_area_set(self, snip_rect):
        """Set the capture area and update the capture_area_set flag."""
        self.capture_area = snip_rect
        self.capture_area_set = True
        logger.info(f"Capture area set to: {self.capture_area}")
        
        if self.capture_in_progress:
            self.capture()
            self.capture_in_progress = False

    def insert_image_with_thumbnail(self, pixmap):
        unique_id = str(uuid4())
        logger.debug(f"Generated unique_id for image: {unique_id}")

        # Generate thumbnail
        thumbnail_pixmap = pixmap.scaled(
            200,
            150,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        logger.debug(f"Thumbnail generated for image ID {unique_id}")

        # Base64 encode the full image
        buffer_full = QBuffer()
        buffer_full.open(QBuffer.OpenModeFlag.ReadWrite)
        pixmap.save(buffer_full, "PNG")
        base64_full_image = base64.b64encode(buffer_full.data()).decode('utf-8')
        buffer_full.close()
        logger.debug(f"Base64 encoding complete for full image with ID {unique_id}, length: {len(base64_full_image)}")

        # Insert HTML thumbnail with link to full image
        editor = self.get_current_editor()
        if editor:
            # Add the thumbnail image to document resources
            editor.document().addResource(
                QTextDocument.ResourceType.ImageResource,
                QUrl(unique_id),
                thumbnail_pixmap,
            )
            logger.debug(f"Thumbnail image resource added to document for ID {unique_id}")

            cursor = editor.textCursor()
            cursor.beginEditBlock()
            cursor.insertText('\u200b')  # Zero-width space for formatting isolation
            html = f'<a href="{unique_id}" onclick="showFullImage(\'data:image/png;base64,{base64_full_image}\')"><img src="{unique_id}" width="200" height="150" style="cursor:pointer;"/></a>'
            cursor.insertHtml(html)
            cursor.movePosition(QTextCursor.MoveOperation.Right)
            cursor.insertText('\u200b')
            cursor.setCharFormat(QTextCharFormat())
            cursor.endEditBlock()
            editor.setTextCursor(cursor)

            # Store images in maps
            self.full_image_map[unique_id] = base64_full_image
            self.thumbnail_image_map[unique_id] = thumbnail_pixmap
            logger.info(f"Full-size image and thumbnail stored for ID {unique_id}")
            
            # Assign maps to editor for access
            editor.full_image_map = self.full_image_map
            editor.thumbnail_image_map = self.thumbnail_image_map


    """------------------------------------------------------------Edit Methods------------------------------------------""" 
    """----------Edit Action Methods----------"""
    def undo(self):
        """Undo the last action in the current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.undo()
            logger.info("Undo action performed.")

    def redo(self):
        """Redo the last undone action in the current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.redo()
            logger.info("Redo action performed.")

    def cut(self):
        """Cut the selected text in the current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.cut()
            logger.info("Cut action performed.")

    def copy(self):
        """Copy the selected text in the current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.copy()
            logger.info("Copy action performed.")

    def paste(self):
        """Paste text from the clipboard into the current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.paste()
            logger.info("Paste action performed.")

    """----------Helper Methods for Edit Actions----------"""
    def get_current_editor(self):
        """Retrieve the currently active editor widget in the tab."""
        return self.tab_widget.currentWidget()

    def get_current_tab_index(self):
        """Get the current index of the active tab."""
        return self.tab_widget.currentIndex() if self.tab_widget.count() > 0 else -1
        
    """------------------------------------------------------File Methods-------------------------------------------------"""     
    """----------File Action Methods----------"""
    def add_new_tab(self, text=None):
        """Add a new untitled tab with a unique incremented name."""
        # Ensure 'text' is a string and defaults to an empty string if None or False
        if not isinstance(text, str):
            text = ""

        # Determine the next available untitled file name
        untitled_count = 1
        existing_titles = [self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]
        existing_files = os.listdir(PERSISTENT_FOLDER)

        while f"Untitled_{untitled_count}.txt" in existing_titles or f"Untitled_{untitled_count}.txt" in existing_files:
            untitled_count += 1
        untitled_name = f"Untitled_{untitled_count}.txt"

        # Create the new tab editor
        new_tab = ClickableTextEdit()
        new_tab.full_image_map = self.full_image_map
        new_tab.setFont(QFont(self.current_font_family, self.current_font_size))
        new_tab.setPlainText(text)

        # Add the new tab with a unique name
        index = self.tab_widget.addTab(new_tab, untitled_name)
        self.tab_widget.setCurrentIndex(index)

        # Set up the custom context menu for the new tab
        self.setup_custom_context_menu()

        # If auto-save is enabled, save the initial file to the persistent folder
        if self.autosave_toggle_button.isChecked():
            persistent_path = os.path.join(PERSISTENT_FOLDER, untitled_name)
            with open(persistent_path, 'w', encoding='utf-8') as f:
                f.write(text)
            self.file_metadata_manager.update_file_metadata(untitled_name, persistent_path, persistent_path)
            self.paths[index] = persistent_path
            self.saved_files_panel.refresh_files_list()
            logger.info(f"Auto-saved initial content to persistent path: {persistent_path}")

    def show_tab_context_menu(self, position):
        """Show context menu for tabs with options to rename or close the current tab."""
        menu = QMenu(self)
        
        # Close Tab action
        close_action = QAction("Close Tab", self)
        close_action.triggered.connect(lambda: self.close_tab(self.tab_widget.tabBar().tabAt(position)))
        menu.addAction(close_action)
        
        # Rename Tab action
        rename_action = QAction("Rename Tab", self)
        rename_action.triggered.connect(lambda: self.rename_tab(self.tab_widget.tabBar().tabAt(position)))
        menu.addAction(rename_action)
        
        menu.exec(self.tab_widget.mapToGlobal(position))

    def rename_tab(self, index):
        """Prompt the user to rename the specified tab."""
        current_name = self.tab_widget.tabText(index)
        new_name, ok = QInputDialog.getText(self, "Rename Tab", "Enter new name:", text=current_name)
        
        if ok and new_name:
            self.tab_widget.setTabText(index, new_name)
            logger.info(f"Tab at index {index} renamed to '{new_name}'.")

    def is_tab_empty(self, editor):
        """Check if the editor tab is empty, meaning it contains no text or images."""
        if editor is None:
            return True  # If there's no editor, consider the tab empty
        return not editor.toPlainText().strip() and not self.has_images(editor)


    def has_images(self, editor):
        """Check if the editor contains any images."""
        if editor is None:
            return False
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        while not cursor.atEnd():
            if cursor.charFormat().isImageFormat():
                return True
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
        return False

    def add_html_tab_from_text(self, text, title="HTML View"):
        """Convert plain text to basic HTML and add it to a new HTML tab."""
        html_tab = QTextEdit()
        html_tab.setFont(QFont(self.current_font_family, self.current_font_size))
        # Convert text to HTML by replacing newlines with <br> tags
        html_tab.setHtml("<html><body>" + text.replace("\n", "<br>") + "</body></html>")
        index = self.tab_widget.addTab(html_tab, title)
        self.tab_widget.setCurrentIndex(index)

    def add_editor_to_tab(self, editor, path):
        """Add the editor to a new tab and set up paths and tab text."""
        index = self.tab_widget.addTab(editor, os.path.basename(path))
        self.paths[index] = path
        self.tab_widget.setCurrentIndex(index)
        self.tab_widget.setTabToolTip(index, path)
        return index
        
    def open_new_instance(self):
        """Open a new instance of the application with a cascaded window position."""
        try:
            # Get the current window position
            current_x = self.x()
            current_y = self.y()

            # Offset for the cascade effect (e.g., 30 pixels down and right)
            offset = 30
            new_x = current_x + offset
            new_y = current_y + offset

            # Start a new instance of the script with position arguments
            subprocess.Popen(["python", __file__, str(new_x), str(new_y)])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open a new instance: {str(e)}")   

    def file_open(self):
        """Open a file, loading its content based on its format (TXT or HTML)."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open file",
            "",
            "Text and HTML documents (*.txt *.html);;All files (*.*)"
        )
        if path:
            try:
                # Determine whether to use the current tab or create a new one
                index = self.get_current_tab_index()
                current_editor = self.tab_widget.widget(index) if index >= 0 else None

                # Check if the current tab exists and is empty and unmodified
                if current_editor and self.is_tab_empty(current_editor) and not current_editor.document().isModified():
                    # Reuse the current tab
                    editor = current_editor
                    self.paths[index] = path
                    self.tab_widget.setTabText(index, os.path.basename(path))
                    self.tab_widget.setTabToolTip(index, path)
                else:
                    # Create a new tab
                    editor = ClickableTextEdit()
                    index = self.tab_widget.addTab(editor, os.path.basename(path))
                    self.paths[index] = path
                    self.tab_widget.setCurrentIndex(index)
                    self.tab_widget.setTabToolTip(index, path)

                # Load the file content into the editor
                self.load_file_content(path, editor)

                logger.info(f"File opened: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
                logger.error(f"Failed to open file: {str(e)}")

    def load_file_content(self, path, editor):
        """Load the content of a file into the provided editor."""
        if path.endswith(".html"):
            self.load_html_file(path, editor)
        else:
            with open(path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            editor.setPlainText(text_content)

    def load_html_content(self, path, editor):
        """Load HTML content, reconstructing images from base64 data."""
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Set the HTML content directly
        editor.setHtml(html_content)

        # Reconstruct images
        document = editor.document()
        resource_iterator = document.allResources()
        for resource_name in resource_iterator:
            if resource_name.type() == QTextDocument.ResourceType.ImageResource:
                image = document.resource(QTextDocument.ResourceType.ImageResource, resource_name)
                if isinstance(image, QPixmap):
                    # Store the image in full_image_map
                    image_id = str(uuid4())
                    self.full_image_map[image_id] = image
                    # Update the image format to use the new ID
                    image_format = QTextImageFormat()
                    image_format.setName(image_id)
                    # Update the document resource
                    document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(image_id), image)
                    
    def open_file_in_new_tab(self, file_path):
        """Open a specified file in a new tab and display its content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        editor = ClickableTextEdit()
        editor.setPlainText(content)
        tab_index = self.tab_widget.addTab(editor, os.path.basename(file_path))
        self.tab_widget.setCurrentIndex(tab_index)
        self.paths[tab_index] = file_path
        logger.info(f"Opened file in new tab: {file_path}")                   
                    

    def load_html_file(self, path, editor):
        """Load an HTML file with images and text into the provided editor, reconstructing images and mappings."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Parse HTML content using BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove all script tags
            for script in soup.find_all('script'):
                script.decompose()

            # Remove all overlay divs with id="overlay"
            for overlay_div in soup.find_all('div', id='overlay'):
                overlay_div.decompose()

            # Remove any buttons with text 'Close'
            for button in soup.find_all('button'):
                if button.get_text(strip=True) == 'Close':
                    button.decompose()

            # Initialize image maps for this editor
            editor.full_image_map = {}
            editor.thumbnail_image_map = {}

            # Iterate over all 'img' tags in the HTML
            for img_tag in soup.find_all('img'):
                # Get the base64 thumbnail image data from the 'src' attribute
                img_src = img_tag.get('src')
                if img_src and img_src.startswith("data:image/png;base64,"):
                    base64_thumbnail = img_src.split("base64,")[1]
                    thumbnail_data = base64.b64decode(base64_thumbnail)
                    thumbnail_pixmap = QPixmap()
                    thumbnail_pixmap.loadFromData(thumbnail_data)

                    # Extract the base64 full image data from the 'onclick' attribute
                    onclick_attr = img_tag.get('onclick')
                    if onclick_attr and "showFullImage" in onclick_attr:
                        # Extract the base64 full image data
                        base64_full_image = onclick_attr.split("base64,")[1].rstrip("')")

                        # Assign a unique ID to this image
                        unique_id = str(uuid4())

                        # Store images in both the editor's and main window's image maps
                        editor.full_image_map[unique_id] = base64_full_image
                        editor.thumbnail_image_map[unique_id] = thumbnail_pixmap
                        self.full_image_map[unique_id] = base64_full_image
                        self.thumbnail_image_map[unique_id] = thumbnail_pixmap

                        # Replace 'src' with the unique ID
                        img_tag['src'] = unique_id

                        # Clear the 'onclick' attribute
                        img_tag['onclick'] = ""

                        # Remove the 'href' attribute from parent 'a' tag if it exists
                        if img_tag.parent and img_tag.parent.name == 'a':
                            img_tag.parent['href'] = unique_id

                        # Add the thumbnail image to the document resources
                        editor.document().addResource(
                            QTextDocument.ResourceType.ImageResource,
                            QUrl(unique_id),
                            thumbnail_pixmap,
                        )
                    else:
                        logger.warning("Full-size image data not found for an image.")
                else:
                    # Handle cases where 'img_src' is not properly set
                    logger.warning("Image source is missing or not in expected format.")

            # Convert the modified soup back to HTML
            modified_html = str(soup)

            # Set the editor's HTML content
            editor.setHtml(modified_html)

            logger.info(f"HTML file '{path}' loaded into editor with images reconstructed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load HTML file: {str(e)}")
            logger.error(f"Failed to load HTML file: {str(e)}")

    def file_save(self, index=None):
        """Save the current document. If the file has not been saved before, perform 'Save As'."""
        if index is None:
            index = self.get_current_tab_index()

        # Check if the file has a path associated with it
        path = self.paths.get(index)

        if not path:
            # If there's no saved path, prompt 'Save As'
            logger.info("No existing save path. Calling 'Save As'.")
            self.file_save_as(index)
        else:
            # Determine whether to save as HTML or plain text based on file extension
            editor = self.tab_widget.widget(index)
            if path.endswith(".html"):
                # Use save_as_html for HTML files
                self.save_as_html_with_js(path, index)
                logger.info(f"File re-saved as HTML with embedded images: {path}")
            else:
                # For non-HTML formats, save as plain text
                content = editor.toPlainText()
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(content)
                editor.document().setModified(False)
                logger.info(f"File re-saved as plain text: {path}")

 
    def file_save_as(self, index=None):
        """Save file to a user-specified location with embedded images and JavaScript for full-size display."""
        if index is None:
            index = self.get_current_tab_index()

        user_path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "", "HTML documents (*.html)"
        )

        if user_path:
            # Use the JavaScript-enabled HTML save method
            self.save_as_html_with_js(user_path, index)


    def save_as_html_with_js(self, path, index):
        """Save the document content as an HTML file with embedded images and JavaScript for full-size image display."""
        logger.info(f"Starting save_as_html_with_js for path: {path} and index: {index}")

        editor = self.tab_widget.widget(index)
        if editor:
            # Step 1: Get HTML content from the editor
            html_content = editor.document().toHtml()
            logger.debug("Original HTML content retrieved from editor.")

            # Step 2: Embed images within HTML content using editor's image maps
            embedded_html_content = self.embed_images_in_html_with_js(html_content, editor.document(), editor)
            logger.debug("HTML content after embedding images.")

            # Step 3: Save the final HTML content with JavaScript and embedded images
            with open(path, 'w', encoding='utf-8') as file:
                file.write(embedded_html_content)
                logger.info(f"Embedded HTML content with JavaScript saved to {path}")

            # Update paths and UI
            self.paths[index] = path
            self.tab_widget.setTabText(index, os.path.basename(path))
            self.tab_widget.setTabToolTip(index, path)
            editor.document().setModified(False)
            logger.info(f"Document saved and UI updated for path: {path}")


    def embed_images_in_html_with_js(self, html_content, document, editor):
        """Embed both thumbnail and full-size images as base64 in HTML with JavaScript for overlay viewing."""
        logger.info("Starting embed_images_in_html_with_js")
        soup = BeautifulSoup(html_content, 'html.parser')

        for img_tag in soup.find_all('img'):
            unique_id = img_tag.get('src')
            logger.debug(f"Found <img> tag with src (unique_id): {unique_id}")

            if unique_id:
                # Retrieve images from the editor's image maps
                base64_full_image = editor.full_image_map.get(unique_id)
                thumbnail_pixmap = editor.thumbnail_image_map.get(unique_id)
                if not base64_full_image or not thumbnail_pixmap:
                    logger.warning(f"No images found in editor's image maps for ID {unique_id}")
                    continue

                # Encode thumbnail image to base64
                buffer = QBuffer()
                buffer.open(QBuffer.OpenModeFlag.ReadWrite)
                thumbnail_pixmap.save(buffer, "PNG")
                base64_thumbnail_image = base64.b64encode(buffer.data()).decode('utf-8')
                buffer.close()

                logger.info(f"Embedding Base64 images directly for ID {unique_id}")

                # Embed the Base64 string in the `src` attribute
                img_tag['src'] = f"data:image/png;base64,{base64_thumbnail_image}"
                # Update the `onclick` attribute for full-size image display
                img_tag['onclick'] = f"showFullImage('data:image/png;base64,{base64_full_image}')"
                img_tag['style'] = "cursor: pointer;"
                if img_tag.parent and img_tag.parent.name == 'a':
                    img_tag.parent['href'] = "javascript:void(0);"

        # Add overlay and script for full-size viewing if not already present
        if not soup.find(id="overlay"):
            logger.info("Adding JavaScript and overlay HTML for full-size image viewing.")
            overlay_script = """
            <script type="text/javascript">
                function showFullImage(fullImageData) {
                    var overlay = document.getElementById('overlay');
                    var fullImage = document.getElementById('fullImage');
                    fullImage.src = fullImageData;
                    overlay.style.display = 'flex';
                }

                function hideFullImage() {
                    document.getElementById('overlay').style.display = 'none';
                }
            </script>
            <div id="overlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%;
                 background-color:rgba(0,0,0,0.8); justify-content:center; align-items:center;">
                <img id="fullImage" src="" style="max-width:90%; max-height:90%;" alt="Full Size"/>
                <button onclick="hideFullImage()" style="position:absolute; top:20px; right:20px;
                        background-color:white; border:none; font-size:18px;">Close</button>
            </div>
            """
            soup.body.append(BeautifulSoup(overlay_script, 'html.parser'))

        logger.info("Completed embed_images_in_html_with_js")
        return str(soup)

    def convert_document_to_html(self, document):
        """Convert a QTextDocument to HTML with embedded images as clickable thumbnails."""
        cursor = QTextCursor(document)
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        html_output = "<html><body>"

        while not cursor.atEnd():
            block = cursor.block()
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                format = fragment.charFormat()

                if format.isImageFormat():
                    image_format = format.toImageFormat()
                    image_id = image_format.name()

                    if image_id in self.full_image_map:
                        pixmap = self.full_image_map[image_id]

                        # Convert full-size image to base64 for embedding in `href`
                        buffer_full = QBuffer()
                        buffer_full.open(QBuffer.OpenModeFlag.ReadWrite)
                        pixmap.save(buffer_full, "PNG")
                        base64_full = base64.b64encode(buffer_full.data()).decode('utf-8')
                        buffer_full.close()

                        # Get thumbnail image from document resources
                        thumbnail_image = document.resource(QTextDocument.ResourceType.ImageResource, QUrl(image_id))
                        
                        if thumbnail_image:
                            # Convert thumbnail to base64 for embedding in `src`
                            buffer_thumb = QBuffer()
                            buffer_thumb.open(QBuffer.OpenModeFlag.ReadWrite)
                            thumbnail_image.save(buffer_thumb, "PNG")
                            base64_thumb = base64.b64encode(buffer_thumb.data()).decode('utf-8')
                            buffer_thumb.close()

                            # Embed the image as a clickable thumbnail
                            width = image_format.width() if image_format.width() else pixmap.width()
                            height = image_format.height() if image_format.height() else pixmap.height()

                            thumbnail_html = (
                                f'<a href="data:image/png;base64,{base64_full}" target="_blank">'
                                f'<img src="data:image/png;base64,{base64_thumb}" '
                                f'width="{width}" height="{height}"/></a>'
                            )
                            html_output += thumbnail_html
                        else:
                            # Log warning if thumbnail not found
                            logger.warning(f"Thumbnail image for ID {image_id} not found in document resources.")
                    else:
                        # Log warning if full-size image not found
                        logger.warning(f"Image with ID {image_id} not found in full_image_map.")
                else:
                    # Handle text
                    text = fragment.text().replace('\n', '<br>')
                    html_output += text

                it += 1  # Move to the next fragment

            cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
            html_output += "<br>"

        html_output += "</body></html>"
        return html_output

    """----------Helper Methods for File Actions----------"""
    def get_current_tab_index(self):
        """Retrieve the current index of the active tab."""
        return self.tab_widget.currentIndex()        
        
    """-----------------------------------------------------------Font Methods-------------------------------------------------"""        
    """----------Font Change Methods----------"""
    def on_font_change(self, font):
        """Update the current font family based on the user's selection and save the setting."""
        self.current_font_family = font.family()
        app_settings["font_family"] = self.current_font_family  # Update settings with new font family
        save_settings(app_settings)  # Persist change to settings
        self.apply_current_font_settings()
        logger.info(f"Font family changed to {self.current_font_family} and saved to settings.")


    def on_fontsize_change(self, size):
        """Update the current font size based on the user's selection and save the setting."""
        try:
            self.current_font_size = int(size)
            app_settings["font_size"] = self.current_font_size  # Update settings with new font size
            save_settings(app_settings)  # Persist change to settings
            self.apply_current_font_settings()
            logger.info(f"Font size changed to {self.current_font_size} and saved to settings.")
        except ValueError:
            logger.error(f"Invalid font size: {size}")

    def clear_formatting(self):
        """Clear all text formatting in the current editor, resetting to theme defaults."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            format = QTextCharFormat()
            format.setFont(QFont(self.current_theme_settings["font_family"], self.current_theme_settings["font_size"]))
            format.setForeground(self.current_theme_settings["text_color"])
            format.setBackground(Qt.GlobalColor.transparent)

            # Apply formatting to selection if there's a selection, otherwise to the cursor position
            if cursor.hasSelection():
                cursor.mergeCharFormat(format)
            else:
                editor.setCurrentFont(QFont(self.current_theme_settings["font_family"], self.current_theme_settings["font_size"]))
                editor.mergeCurrentCharFormat(format)
            
            logger.info("Cleared formatting to current theme defaults.")

    """----------Helper Methods for Font Application----------"""
    def apply_current_font_settings(self):
        """Apply the current font settings (family and size) to the text at the cursor or selected text and save in settings."""
        editor = self.get_current_editor()
        if editor:
            # Get the current text cursor and define the text format with font family and size
            cursor = editor.textCursor()
            format = QTextCharFormat()
            format.setFontFamily(self.current_font_family)
            format.setFontPointSize(self.current_font_size)

            # Apply format only to selected text, or at cursor position if no text is selected
            if cursor.hasSelection():
                cursor.setCharFormat(format)
            else:
                editor.setCurrentFont(QFont(self.current_font_family, self.current_font_size))
                cursor.mergeCharFormat(format)

            # Save the font settings to app settings for persistence
            app_settings["font_family"] = self.current_font_family
            app_settings["font_size"] = self.current_font_size
            save_settings(app_settings)  # Save settings to JSON file

            logger.info(f"Applied and saved font family '{self.current_font_family}' and size '{self.current_font_size}' at cursor position or selection.")

    def apply_default_font_settings(self):
            """Apply the default font settings to the active editor based on current settings."""
            editor = self.get_current_editor()
            if editor:
                # Use the current font family and size from app_settings for default settings
                editor.setFont(QFont(self.current_font_family, self.current_font_size))
                # Update the cursor format to reflect font settings if typing in the document
                cursor = editor.textCursor()
                format = QTextCharFormat()
                format.setFontFamily(self.current_font_family)
                format.setFontPointSize(self.current_font_size)
                cursor.mergeCharFormat(format)
                editor.setTextCursor(cursor)
                logger.info(f"Applied font settings: {self.current_font_family}, {self.current_font_size}pt") 
 
    """--------------------------------------------------------------Formatting Methods------------------------------------------"""
    """----------Text Formatting Toggle Methods----------"""
    def toggle_text_format(self, format_type, checked):
        """Toggle text format based on format type."""
        editor = self.get_current_editor()
        cursor = editor.textCursor()
        format = QTextCharFormat()

        if format_type == "bold":
            format.setFontWeight(QFont.Weight.Bold if checked else QFont.Weight.Normal)
        elif format_type == "italic":
            format.setFontItalic(checked)
        elif format_type == "underline":
            format.setFontUnderline(checked)
        elif format_type == "strikethrough":
            format.setFontStrikeOut(checked)

        cursor.mergeCharFormat(format)
        editor.setTextCursor(cursor)

    def toggle_highlighting(self, checked):
        """Toggle highlighting on/off with the current highlight color if checked."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            format = cursor.charFormat()
            if checked:
                format.setBackground(self.current_highlight_color["highlight"])
                format.setForeground(self.current_highlight_color["font"])
            else:
                format.setBackground(Qt.GlobalColor.transparent)
                format.setForeground(self.current_theme_settings["text_color"])

            cursor.mergeCharFormat(format)
            editor.setTextCursor(cursor)

    """----------Highlight Color Selection Methods----------"""
    def on_highlight_color_selected(self):
        """Update the current highlight color and apply it immediately if highlighting is active."""
        action = self.sender()
        color = action.data()  # Retrieve color data from the QAction
        self.current_highlight_color = color  # Update the active highlight color
        if self.highlight_action.isChecked():
            self.apply_highlight_style(color)

    def create_highlight_action(self, name, colors):
        """Create a QAction with a preview label for the dropdown highlight color menu."""
        action = QWidgetAction(self)
        label = QLabel(name)
        label.setFont(QFont(DEFAULT_FONT_FAMILY, 12))
        label.setStyleSheet(
            f"background-color: rgb({colors['highlight'].red()}, {colors['highlight'].green()}, {colors['highlight'].blue()}); "
            f"color: rgb({colors['font'].red()}, {colors['font'].green()}, {colors['font'].blue()}); "
            "padding: 5px; margin: 1px;"
        )
        action.setDefaultWidget(label)
        return action

    def apply_highlight_style(self, color):
        """Apply the selected highlight color to the text cursor or selection, merging with other styles."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            format = cursor.charFormat()
            format.setBackground(color["highlight"])
            format.setForeground(color["font"])

            if cursor.hasSelection():
                cursor.setCharFormat(format)
            else:
                cursor.mergeCharFormat(format)

            editor.setTextCursor(cursor)
            editor.setFocus()
 
    """-------------------------------------------------------------List Methods--------------------------------------"""
    """----------List Action Methods----------"""
    def add_bullet_list(self):
        """Apply a bullet list format to the selected text or current line."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()
            
            # Toggle bullet list
            current_list = cursor.currentList()
            if current_list and current_list.format().style() == QTextListFormat.Style.ListDisc:
                block_format = cursor.blockFormat()
                block_format.setIndent(0)
                cursor.setBlockFormat(block_format)
            else:
                list_format = QTextListFormat()
                list_format.setStyle(QTextListFormat.Style.ListDisc)
                cursor.createList(list_format)
            
            cursor.endEditBlock()
            logger.info("Bullet list applied.")

    def add_numbered_list(self):
        """Apply a numbered list format to the selected text or current line."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()

            # Toggle numbered list
            current_list = cursor.currentList()
            if current_list and current_list.format().style() == QTextListFormat.Style.ListDecimal:
                block_format = cursor.blockFormat()
                block_format.setIndent(0)
                cursor.setBlockFormat(block_format)
            else:
                list_format = QTextListFormat()
                list_format.setStyle(QTextListFormat.Style.ListDecimal)
                cursor.createList(list_format)
            
            cursor.endEditBlock()
            logger.info("Numbered list applied.")

    def increase_indent(self):
        """Increase the indent level of the selected text or current line."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()

            # Increase indent level
            block_format = cursor.blockFormat()
            block_format.setIndent(block_format.indent() + 1)
            cursor.setBlockFormat(block_format)
            
            cursor.endEditBlock()
            logger.info("Increased indent level.")

    def decrease_indent(self):
        """Decrease the indent level of the selected text or current line."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()

            # Decrease indent level with a minimum of 0
            block_format = cursor.blockFormat()
            block_format.setIndent(max(block_format.indent() - 1, 0))
            cursor.setBlockFormat(block_format)
            
            cursor.endEditBlock()
            logger.info("Decreased indent level.")
 
    """------------------------------------------------------------Spell Check Methods-----------------------------------""" 
    """----------Spell Check Toggle Method----------"""
    def toggle_real_time_spell_check(self, checked):
        """Enable or disable real-time spell check based on the toggle state, preserving images."""
        editor = self.get_current_editor()
        if checked:
            self.spell_check_timer = QTimer()
            self.spell_check_timer.setSingleShot(True)
            self.spell_check_timer.timeout.connect(self.perform_real_time_spell_check)
            
            # Connect to text changes only if there's an active editor
            if editor:
                editor.textChanged.connect(lambda: self.spell_check_timer.start(500))
            logger.info("Real-time spell check enabled.")
        else:
            # Disconnect spell check to prevent interference
            if editor:
                try:
                    editor.textChanged.disconnect()
                except TypeError:
                    pass  # Safe disconnect if already disconnected
            logger.info("Real-time spell check disabled.")


    """----------Real-Time Spell Check Method----------"""
    def perform_real_time_spell_check(self):
        """Underline misspelled words in real-time without affecting images or other formatting."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()

            block = editor.document().firstBlock()
            while block.isValid():
                it = block.begin()
                while not it.atEnd():
                    fragment = it.fragment()
                    if fragment.isValid():
                        # Check if the fragment is an image
                        if fragment.charFormat().isImageFormat():
                            pass  # Skip image fragments
                        else:
                            # Get the start and end positions of the fragment
                            start_pos = fragment.position()
                            end_pos = start_pos + fragment.length()

                            # Create a cursor for the fragment
                            fragment_cursor = QTextCursor(editor.document())
                            fragment_cursor.setPosition(start_pos)
                            fragment_cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)

                            # Remove existing spell check underlines from this fragment
                            format = QTextCharFormat()
                            format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.NoUnderline)
                            fragment_cursor.mergeCharFormat(format)

                            # Get the text of the fragment
                            text = fragment.text()
                            if text:
                                self.check_text_fragment(fragment_cursor, text)
                    it += 1
                block = block.next()
            cursor.endEditBlock()


    def check_text_fragment(self, cursor, text):
        """Check a text fragment for spelling errors and apply underlines."""
        # Tokenize the text into words using regular expressions
        words = re.finditer(r'\b\w+\b', text)
        for word_match in words:
            word = word_match.group()
            start_offset = word_match.start()
            end_offset = word_match.end()

            # Calculate the absolute positions
            start = cursor.selectionStart() + start_offset
            end = cursor.selectionStart() + end_offset

            word_cursor = QTextCursor(cursor.document())
            word_cursor.setPosition(start)
            word_cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

            if word not in spell:
                # Apply spell check underline
                misspelled_format = QTextCharFormat()
                misspelled_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
                misspelled_format.setUnderlineColor(Qt.GlobalColor.red)
                word_cursor.mergeCharFormat(misspelled_format)


    """----------Custom Context Menu for Spell Check Suggestions----------"""
    def setup_custom_context_menu(self):
        editor = self.get_current_editor()
        if editor:
            editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            editor.customContextMenuRequested.connect(self.show_custom_context_menu)

    def show_custom_context_menu(self, pos):
        """Create a custom context menu with text editing, spell-check, and formatting options in a gray color scheme."""
        editor = self.get_current_editor()
        if not editor:
            return  # Exit if there's no active editor

        # Initialize the context menu with a gray color scheme
        context_menu = QMenu(editor)
        context_menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;  /* Dark gray background */
                color: #f0f0f0;             /* Light gray text */
                border: 1px solid #5a5a5a;  /* Border color */
            }
            QMenu::item {
                background-color: transparent;
                padding: 4px 24px;
            }
            QMenu::item:selected {
                background-color: #3a3a3a;  /* Slightly lighter gray on selection */
                color: #ffffff;             /* White text on selection */
            }
            QMenu::separator {
                height: 1px;
                background: #5a5a5a;        /* Gray separator line */
                margin-left: 10px;
                margin-right: 10px;
            }
        """)

        # Basic editing actions
        cut_action = QAction("Cut", editor)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(editor.cut)
        context_menu.addAction(cut_action)

        copy_action = QAction("Copy", editor)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(editor.copy)
        context_menu.addAction(copy_action)

        paste_action = QAction("Paste", editor)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(editor.paste)
        context_menu.addAction(paste_action)

        delete_action = QAction("Delete", editor)
        delete_action.triggered.connect(lambda: editor.textCursor().removeSelectedText())
        context_menu.addAction(delete_action)

        context_menu.addSeparator()

        # Get the cursor at the position where the context menu was requested
        cursor = editor.cursorForPosition(pos)
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText()
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()

        if word and word not in spell:
            spell_menu = QMenu("Spelling Suggestions", editor)
            spell_menu.setStyleSheet(context_menu.styleSheet())  # Apply gray color scheme

            # Get suggestions
            suggestions = spell.candidates(word)
            if suggestions:
                for suggestion in suggestions:
                    action = QAction(suggestion, editor)
                    action.triggered.connect(lambda _, sug=suggestion, s=start_pos, e=end_pos: self.replace_word(editor, s, e, sug))
                    spell_menu.addAction(action)

            add_to_dict_action = QAction("Add to Dictionary", editor)
            add_to_dict_action.triggered.connect(lambda _, w=word: self.add_word_to_dictionary(w))
            spell_menu.addAction(add_to_dict_action)

            context_menu.addMenu(spell_menu)

        context_menu.addSeparator()

        # Text formatting options
        bold_action = QAction("Bold", editor)
        bold_action.setCheckable(True)
        bold_action.setChecked(editor.fontWeight() == QFont.Weight.Bold)
        bold_action.triggered.connect(lambda: self.toggle_text_format("bold", bold_action.isChecked()))
        context_menu.addAction(bold_action)

        italic_action = QAction("Italic", editor)
        italic_action.setCheckable(True)
        italic_action.setChecked(editor.fontItalic())
        italic_action.triggered.connect(lambda: self.toggle_text_format("italic", italic_action.isChecked()))
        context_menu.addAction(italic_action)

        underline_action = QAction("Underline", editor)
        underline_action.setCheckable(True)
        underline_action.setChecked(editor.fontUnderline())
        underline_action.triggered.connect(lambda: self.toggle_text_format("underline", underline_action.isChecked()))
        context_menu.addAction(underline_action)

        strikethrough_action = QAction("Strikethrough", editor)
        strikethrough_action.setCheckable(True)
        strikethrough_action.triggered.connect(lambda: self.toggle_text_format("strikethrough", strikethrough_action.isChecked()))
        context_menu.addAction(strikethrough_action)

        # Highlight options (with a submenu for color selection)
        highlight_menu = QMenu("Highlight", editor)
        highlight_menu.setStyleSheet(context_menu.styleSheet())  # Apply gray color scheme
        for name, colors in HIGHLIGHT_STYLES.items():
            color_action = QAction(name, editor)
            color_action.triggered.connect(lambda _, col=colors: self.apply_highlight_style(col))
            highlight_menu.addAction(color_action)
        context_menu.addMenu(highlight_menu)

        # Show the context menu at the global position
        context_menu.exec(editor.viewport().mapToGlobal(pos))
            
    def populate_spell_check_menu(self, word, cursor, spell_check_menu):
        suggestions = spell.candidates(word)
        for suggestion in suggestions:
            action = QAction(suggestion, self)
            action.triggered.connect(lambda _, sug=suggestion: self.replace_word(cursor, sug))
            spell_check_menu.addAction(action)
        
        add_to_dict_action = QAction("Add to Dictionary", self)
        add_to_dict_action.triggered.connect(lambda _, w=word: self.add_word_to_dictionary(w))
        spell_check_menu.addAction(add_to_dict_action)

    """----------Dictionary Management Methods----------"""
    def replace_word(self, editor, start_pos, end_pos, replacement):
        """Replace the word at the given position with the provided replacement."""
        cursor = QTextCursor(editor.document())
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(replacement)
        cursor.endEditBlock()
        # Re-run spell check to update underlines
        self.perform_real_time_spell_check()

    def add_word_to_dictionary(self, word):
        """Add a word to the custom dictionary."""
        spell.word_frequency.add(word)
        self.save_custom_dictionary()
        QMessageBox.information(self, "Word Added", f"'{word}' has been added to the dictionary.")
        # Re-run spell check to update underlines
        self.perform_real_time_spell_check()

    def save_custom_dictionary(self):
        with open(CUSTOM_DICT_PATH, 'w') as f:
            json.dump(list(spell.word_frequency.dictionary.keys()), f, indent=4)
        logger.info("Custom dictionary saved.")
        
    def edit_custom_dictionary(self):
        dialog = CustomDictionaryDialog(self)
        dialog.exec()

"""===========Clicable Text Edit Class-----------"""
class ClickableTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.full_image_map = {}  # To store full images

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            click_pos = event.position().toPoint()
            anchor = self.anchorAt(click_pos)
            
            if anchor:
                image_id = anchor
                if image_id in self.full_image_map:
                    self.show_full_image(self.full_image_map[image_id])
                    return  # Consume the event
            else:
                # Check if the click is adjacent to an image and reset formatting
                cursor = self.cursorForPosition(click_pos)
                cursor.select(QTextCursor.SelectionType.WordUnderCursor)

                # Clear formatting if zero-width space detected
                if cursor.selectedText() == '\u200b':
                    neutral_format = QTextCharFormat()
                    cursor.setCharFormat(neutral_format)
                    self.setTextCursor(cursor)
                
        super().mousePressEvent(event)

    def show_full_image(self, base64_image_data):
        """Display the full-size image in a separate dialog or label."""
        # Decode the base64 data and load it into a QPixmap
        image_data = base64.b64decode(base64_image_data)
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(image_data))
        
        # Create a label or dialog to display the full-size image
        full_image_label = QLabel()
        full_image_label.setPixmap(pixmap)
        full_image_label.setWindowTitle("Full-Size Image")
        full_image_label.setScaledContents(True)
        full_image_label.setFixedSize(pixmap.size())
        
        # Display the full-size image in a modal dialog
        full_image_dialog = QDialog(self)
        layout = QVBoxLayout()
        layout.addWidget(full_image_label)
        full_image_dialog.setLayout(layout)
        full_image_dialog.exec()

"""===========Custom Dictionary Dialog Class=========="""   
class CustomDictionaryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Custom Dictionary")
        layout = QVBoxLayout(self)
        
        # Search bar for filtering words
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search for a word...")
        self.search_bar.textChanged.connect(self.filter_words)
        layout.addWidget(self.search_bar)

        # Word list display
        self.word_list = QListWidget(self)
        self.word_list.setSortingEnabled(True)
        layout.addWidget(self.word_list)

        # Load and display words
        self.words = []  # Store all words for easy filtering
        self.load_words()

        # Add layout and buttons for adding and removing words
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_changes)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        add_button = QPushButton("Add Word")
        add_button.clicked.connect(self.add_word)
        layout.addWidget(add_button)

        remove_button = QPushButton("Remove Selected Word")
        remove_button.clicked.connect(self.remove_selected_word)
        layout.addWidget(remove_button)

    def load_words(self):
        """Load words from the custom dictionary file, keeping the list sorted."""
        if os.path.exists(CUSTOM_DICT_PATH):
            with open(CUSTOM_DICT_PATH, 'r') as f:
                self.words = sorted(json.load(f))
            self.word_list.addItems(self.words)

    def filter_words(self):
        """Filter the word list based on the search bar input."""
        search_text = self.search_bar.text().lower()
        self.word_list.clear()
        
        # Add only matching words to the list
        for word in self.words:
            if search_text in word.lower():
                self.word_list.addItem(word)

    def save_changes(self):
        """Save the current words in alphabetical order."""
        current_words = [self.word_list.item(i).text() for i in range(self.word_list.count())]
        with open(CUSTOM_DICT_PATH, 'w') as f:
            json.dump(sorted(current_words), f, indent=4)
        spell.word_frequency.load_words(current_words)  # Update the spell checker
        self.accept()

    def add_word(self):
        """Add a new word to the list and update display."""
        text, ok = QInputDialog.getText(self, "Add Word", "Enter word to add:")
        if ok and text:
            self.words.append(text)
            self.words.sort()  # Keep the list sorted
            self.filter_words()  # Re-filter to reflect the added word

    def remove_selected_word(self):
        """Remove selected word(s) from the list and update the display."""
        for item in self.word_list.selectedItems():
            self.words.remove(item.text())
            self.word_list.takeItem(self.word_list.row(item))
            
class CustomSplitterHandle(QSplitterHandle):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.init_ui()

    def init_ui(self):
        # Set up the handle layout with only the grip label
        layout = QVBoxLayout() if self.orientation() == Qt.Orientation.Vertical else QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)

        # Create the grip label for visual feedback
        grip_label = QLabel("|||", self)  # Using "|||" as a visual cue for grip
        grip_label.setFixedSize(QSize(40, 40))
        grip_label.setStyleSheet("background-color: #888; font-size: 14px; color: white;")
        
        layout.addWidget(grip_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

class CustomSplitter(QSplitter):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

    def createHandle(self):
        """Override to use the custom splitter handle."""
        return CustomSplitterHandle(self.orientation(), self)
      
class SavedFilesPanel(QWidget):
    """A panel to display saved files on the left side of the main window, with toggle and collapse functionality."""
    def __init__(self, main_window):
        super(SavedFilesPanel, self).__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle("Saved Files")
        self.setFixedWidth(200)

        # Initialize layout and widgets
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Header layout for collapse and toggle button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)

        # Collapse button for hiding the panel
        self.collapse_button = QPushButton("◀", self)
        font = self.collapse_button.font()
        font.setPointSize(16)  
        self.collapse_button.setFont(font) 
        self.collapse_button.setFixedSize(20, 20)

        self.collapse_button.clicked.connect(self.collapse_panel)
        header_layout.addWidget(self.collapse_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # Toggle button for showing/hiding the panel content
        self.toggle_button = QPushButton(self)
        self.toggle_button.setIcon(QIcon.fromTheme("window-close"))  # Uses a standard "X" close icon
        self.toggle_button.setFixedSize(8, 8)
        self.toggle_button.clicked.connect(self.toggle_panel)

        header_layout.addWidget(self.toggle_button, alignment=Qt.AlignmentFlag.AlignRight)

        # Add the header layout to the main layout
        self.layout.addLayout(header_layout)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search files...")
        self.search_bar.textChanged.connect(self.refresh_files_list)
        self.layout.addWidget(self.search_bar)

        # Horizontal layout for sort options and order toggle
        sort_layout = QHBoxLayout()

        # Sort criteria combo box
        self.sort_by_combo = QComboBox()
        self.sort_by_combo.setFixedWidth(150) 
        self.sort_by_combo.addItems(["Name", "Modification Date", "Creation Date"])
        self.sort_by_combo.currentIndexChanged.connect(self.refresh_files_list)
        sort_layout.addWidget(self.sort_by_combo)

        # Sorting direction button (arrow up/down)
        self.sort_order_button = QPushButton("▲")
        self.sort_order_button.setFixedSize(25, 25)
        self.sort_order_button.setCheckable(True)
        self.sort_order_button.clicked.connect(self.toggle_sort_order)
        sort_layout.addWidget(self.sort_order_button)
        self.sort_ascending = True  # Default sort order

        # Add the sort layout to the main layout
        self.layout.addLayout(sort_layout)

        # Saved files list
        self.saved_files_list = QListWidget(self)
        self.layout.addWidget(self.saved_files_list)

        # Context menu for file actions
        self.saved_files_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.saved_files_list.customContextMenuRequested.connect(self.show_context_menu)

        # Manual refresh button
        self.refresh_button = QPushButton("Refresh 🔄")
        self.refresh_button.clicked.connect(self.refresh_files_list)
        self.layout.addWidget(self.refresh_button)

        # Initial load of saved files
        self.refresh_files_list()

    def refresh_files_list(self):
        """Refresh the saved files list based on search, sort options, and sorting preferences."""
        self.saved_files_list.clear()  # Clear the current list

        # Retrieve and filter files
        search_text = self.search_bar.text().lower()
        all_files = [
            f for f in os.listdir(PERSISTENT_FOLDER)
            if os.path.isfile(os.path.join(PERSISTENT_FOLDER, f)) and f != "file_metadata.json"
        ]
        
        # Filter files by search text
        filtered_files = [f for f in all_files if search_text in f.lower()]

        # Sort files based on selected criteria
        sort_criteria = self.sort_by_combo.currentText()
        reverse_order = not self.sort_ascending

        if sort_criteria == "Name":
            sorted_files = sorted(filtered_files, reverse=reverse_order)
        else:
            sorted_files = sorted(
                filtered_files,
                key=lambda f: os.path.getmtime(os.path.join(PERSISTENT_FOLDER, f)) if sort_criteria == "Modification Date"
                else os.path.getctime(os.path.join(PERSISTENT_FOLDER, f)),
                reverse=reverse_order
            )

        # Add sorted and filtered files to the list
        self.saved_files_list.addItems(sorted_files)

    def toggle_panel(self):
        """Toggle visibility of the saved files panel content."""
        is_visible = self.isVisible()
        self.setVisible(not is_visible)
        self.main_window.toggle_panel_action.setChecked(not is_visible)


    def collapse_panel(self):
        """Collapse the splitter panel containing this widget."""
        splitter = self.main_window.splitter  # Access the main splitter
        splitter.setSizes([0, 1])  # Collapse the left panel (self)

    def toggle_sort_order(self):
        """Toggle the sort order between ascending and descending with an arrow button."""
        self.sort_ascending = not self.sort_ascending
        self.sort_order_button.setText("▲" if self.sort_ascending else "▼")
        self.refresh_files_list()  # Refresh the list to apply the new sort order

    def show_context_menu(self, pos):
        """Show context menu for file actions in the saved files list with a gray color scheme."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;  /* Dark gray background */
                color: #f0f0f0;             /* Light gray text */
                border: 1px solid #5a5a5a;  /* Border color */
            }
            QMenu::item {
                background-color: transparent;
                padding: 4px 24px;
            }
            QMenu::item:selected {
                background-color: #3a3a3a;  /* Slightly lighter gray on selection */
                color: #ffffff;             /* White text on selection */
            }
            QMenu::separator {
                height: 1px;
                background: #5a5a5a;        /* Gray separator line */
                margin-left: 10px;
                margin-right: 10px;
            }
        """)

        open_action = QAction("Open", self)
        open_action.triggered.connect(lambda: self.open_selected_file(self.saved_files_list.currentItem()))
        menu.addAction(open_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_selected_file())
        menu.addAction(delete_action)

        properties_action = QAction("Properties", self)
        properties_action.triggered.connect(lambda: self.show_file_properties(self.saved_files_list.currentItem()))
        menu.addAction(properties_action)

        menu.exec(self.saved_files_list.mapToGlobal(pos))

    def add_saved_file(self, file_name):
        """Add a new file to the saved files folder and refresh the list."""
        if not os.path.exists(os.path.join(PERSISTENT_FOLDER, file_name)):
            self.saved_files_list.addItem(file_name)
            self.refresh_files_list()

    def open_selected_file(self, item):
        """Open the selected file in a new tab."""
        if item:
            file_name = item.text()
            file_path = os.path.join(PERSISTENT_FOLDER, file_name)
            if os.path.exists(file_path):
                # Check if the file is already open in a tab
                for index in range(self.main_window.tab_widget.count()):
                    tab_path = self.main_window.paths.get(index)
                    if tab_path == file_path:
                        self.main_window.tab_widget.setCurrentIndex(index)
                        return
                # Open the file in a new tab if not already open
                self.main_window.open_file_in_new_tab(file_path)
            else:
                QMessageBox.warning(self, "File Not Found", f"The file '{file_name}' could not be found.")
                self.refresh_files_list()  # Refresh the list if the file is missing

    def delete_selected_file(self):
        """Delete the selected file and close the corresponding tab if it is open."""
        item = self.saved_files_list.currentItem()
        if item:
            file_name = item.text()
            file_path = os.path.join(PERSISTENT_FOLDER, file_name)

            # Confirm deletion
            confirm = QMessageBox.question(
                self, 
                "Delete File", 
                f"Are you sure you want to delete '{file_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if confirm == QMessageBox.StandardButton.Yes:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.saved_files_list.takeItem(self.saved_files_list.row(item))
                    self.main_window.file_metadata_manager.remove_metadata_entry(file_name)

                    # Close the corresponding tab if open
                    for index in range(self.main_window.tab_widget.count()):
                        tab_path = self.main_window.paths.get(index)
                        if tab_path == file_path:
                            self.main_window.tab_widget.removeTab(index)
                            del self.main_window.paths[index]
                            break
                    self.refresh_files_list()
                    logging.info(f"File '{file_name}' deleted from saved files and any open tab closed.")

    def show_file_properties(self, item):
        """Show the properties of the selected file, including location, created/modified times, and size."""
        if item:
            file_name = item.text()
            file_path = os.path.join(PERSISTENT_FOLDER, file_name)

            if os.path.exists(file_path):
                file_info = os.stat(file_path)
                created_time = datetime.fromtimestamp(file_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                modified_time = datetime.fromtimestamp(file_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                file_size = file_info.st_size

                # Display file properties in a message box
                QMessageBox.information(
                    self, 
                    "File Properties", 
                    f"File: {file_name}\n\n"
                    f"Location: {file_path}\n"
                    f"Created: {created_time}\n"
                    f"Modified: {modified_time}\n"
                    f"Size: {file_size} bytes"
                )
            else:
                QMessageBox.warning(self, "File Not Found", f"The file '{file_name}' could not be found.")
                self.refresh_files_list()
                
class FileMetadataManager:
    """Handles file metadata management, including loading, saving, and updating file paths."""
    
    def __init__(self, metadata_file=METADATA_FILE):
        self.metadata_file = metadata_file
        self.metadata = self.load_metadata()

    def load_metadata(self):
        """Load file metadata from JSON, or initialize as empty if the file doesn't exist."""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}

    def save_metadata(self):
        """Persist the metadata dictionary to JSON."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=4)

    def update_file_metadata(self, file_name, user_path, persistent_path):
        """Update metadata to include both the user-selected and persistent paths."""
        self.metadata[file_name] = {
            "user_path": user_path,  # The path chosen by the user
            "persistent_path": persistent_path,  # The path in the app's persistent folder
            "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": self.metadata.get(file_name, {}).get(
                "created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
        }
        self.save_metadata()

    def remove_metadata_entry(self, file_name):
        """Remove an entry from the metadata if the file is deleted or no longer exists."""
        if file_name in self.metadata:
            del self.metadata[file_name]
            self.save_metadata()

"""===========Snipping Overlay Class=========="""
class SnippingOverlay(QWidget):
    snipCompleteGlobal = pyqtSignal(QRect)

    def __init__(self, screen_rect, close_all_callback):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(screen_rect)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.begin = QPoint()
        self.end = QPoint()
        self.close_all_callback = close_all_callback

    def updateMask(self):
        # Create a mask with the entire area filled
        mask = QBitmap(self.size())
        mask.fill(Qt.GlobalColor.black)
        
        # Define the selection rectangle
        selection_rect = QRect(self.begin, self.end).normalized()

        # Use QPainter to clear the selected area in the mask
        painter = QPainter(mask)
        painter.setBrush(Qt.GlobalColor.white)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(selection_rect)
        painter.end()

        # Apply the mask to make the selection area transparent
        self.setMask(mask)

    def paintEvent(self, event):
        qp = QPainter(self)
        screen_rect = self.rect()

        # Draw a semi-transparent overlay over the entire screen
        qp.setBrush(QColor(0, 0, 0, 100))  # Semi-transparent dark overlay
        qp.setPen(Qt.PenStyle.NoPen)
        qp.drawRect(screen_rect)

        # Draw a clear border around the selection rectangle
        selection_rect = QRect(self.begin, self.end).normalized()
        if not selection_rect.isNull():
            qp.setPen(QPen(Qt.GlobalColor.red, 3))  # Red outline for selection
            qp.drawRect(selection_rect)

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = self.begin
        self.updateMask()
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.updateMask()
        self.update()

    def mouseReleaseEvent(self, event):
        self.end = event.pos()
        self.updateMask()
        self.update()
        # Adjust the coordinates to global
        snip_rect = QRect(self.mapToGlobal(self.begin), self.mapToGlobal(self.end)).normalized()
        self.snipCompleteGlobal.emit(snip_rect)
        self.close_all_callback(snip_rect)
        self.close()  

"""------------------------------------------------------------------------Main Function----------------------------------------"""
# Main Application Execution
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Path to the icon in the images folder
    icon_path = os.path.join(os.path.dirname(__file__), "images", "cano.ico")
    
    # Set the global application icon
    app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())