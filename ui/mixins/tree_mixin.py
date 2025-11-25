from PySide6.QtWidgets import QMenu, QTreeWidgetItem, QMessageBox, QInputDialog
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont
from core import db
from core.db import UNCATEGORIZED
from core.styled_tree import StyledTreeWidget
import re

class CategoryTreeWidget(StyledTreeWidget):

    def __init__(self, owner):
        super().__init__(owner)
        self._owner = owner
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def _event_item(self, event):
        try:
            pos = event.position().toPoint()
        except AttributeError:
            pos = event.pos()
        return self.itemAt(pos)
    
    def _is_table_drag(self, event) -> bool:
        table = getattr(self._owner, "table", None)
        return table is not None and event.source() is table

    def _should_accept_drag(self, event) -> bool:
        if not self._is_table_drag(event):
            return False

        item = self._event_item(event)
        if item is None:
            return False

        try:
            if hasattr(self._owner, "_is_special_folder") and self._owner._is_special_folder(item):
                return False
        except Exception:
            pass

        path = None
        try:
            if hasattr(self._owner, "current_item_path"):
                path = self._owner.current_item_path(item)
        except Exception:
            path = None

        if not path:
            return False

        if path in (
            getattr(self._owner, "SPECIAL_ARCHIVED", "__SPECIAL_ARCHIVED__"),
            getattr(self._owner, "SPECIAL_EXPIRED", "__SPECIAL_EXPIRED__"),
            getattr(self._owner, "SPECIAL_DELETED", "__SPECIAL_DELETED__"),
            UNCATEGORIZED,
        ):
            return False

        return True

    def dragEnterEvent(self, event):
        if self._is_table_drag(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._should_accept_drag(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self._should_accept_drag(event):
            event.ignore()
            return

        item = self._event_item(event)
        if item is None:
            event.ignore()
            return

        target_path = None
        try:
            if hasattr(self._owner, "current_item_path"):
                target_path = self._owner.current_item_path(item)
        except Exception:
            target_path = None

        if not target_path:
            event.ignore()
            return

        ids = []
        try:
            if hasattr(self._owner, "_get_all_selected_entry_ids"):
                ids = self._owner._get_all_selected_entry_ids()
        except Exception:
            ids = []

        if not ids:
            event.ignore()
            return

        mover = getattr(self._owner, "_move_entries_to_category", None)
        if callable(mover):
            mover(ids, target_path)
            event.acceptProposedAction()
        else:
            event.ignore()

class TreeMixin:
    SPECIAL_ARCHIVED = "__SPECIAL_ARCHIVED__"
    SPECIAL_EXPIRED = "__SPECIAL_EXPIRED__"
    SPECIAL_DELETED = "__SPECIAL_DELETED__"

    def _clean_label(self, s: str) -> str:
        return re.sub(r"\s*\(\d+\)\s*$", "", s or "")

    def _ensure_tree_item(self, full_path: str) -> QTreeWidgetItem:
        if full_path in self._path_items:
            return self._path_items[full_path]

        parts = [self._clean_label(p) for p in full_path.split("/") if p]
        parent_item = None
        built = ""
        for part in parts:
            built = part if not built else f"{built}/{part}"
            item = self._path_items.get(built)
            if not item:
                item = QTreeWidgetItem([part])
                item.setData(0, Qt.UserRole, built)
                if parent_item is None:
                    self.tree.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)
                self._path_items[built] = item
            parent_item = item

        return parent_item

    def _init_tree_view(self):
        if not hasattr(self, "tree") or not isinstance(self.tree, CategoryTreeWidget):
            self.tree = CategoryTreeWidget(self)

        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(False)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.expandAll()

    def _create_special_folder_item(self, label: str, identifier: str, count: int, icon_text: str = None) -> QTreeWidgetItem:
        display_text = f"{label} ({count})"
        item = QTreeWidgetItem([display_text])
        item.setData(0, Qt.UserRole, identifier)
        
        font = QFont()
        font.setItalic(True)
        item.setFont(0, font)
        
        if icon_text:
            item.setData(0, Qt.UserRole + 1, icon_text)
        
        item.setData(0, Qt.UserRole + 2, True)
        
        return item

    def _is_special_folder(self, item: QTreeWidgetItem) -> bool:
        if not item:
            return False
        return bool(item.data(0, Qt.UserRole + 2))

    def _add_special_folders(self):
        try:
            counts = db.get_status_counts()
            
            archived_count = counts.get("archived", 0)
            expired_count = counts.get("expired", 0)
            deleted_count = counts.get("deleted", 0)
            
            if archived_count > 0:
                archived_item = self._create_special_folder_item(
                    "Archived", 
                    self.SPECIAL_ARCHIVED, 
                    archived_count,
                    "inventory_2"
                )
                self.tree.addTopLevelItem(archived_item)
                self._path_items[self.SPECIAL_ARCHIVED] = archived_item
            
            if expired_count > 0:
                expired_item = self._create_special_folder_item(
                    "Expired", 
                    self.SPECIAL_EXPIRED, 
                    expired_count,
                    "error"
                )
                self.tree.addTopLevelItem(expired_item)
                self._path_items[self.SPECIAL_EXPIRED] = expired_item
            
            if deleted_count > 0:
                deleted_item = self._create_special_folder_item(
                    "Deleted", 
                    self.SPECIAL_DELETED, 
                    deleted_count,
                    "delete"
                )
                self.tree.addTopLevelItem(deleted_item)
                self._path_items[self.SPECIAL_DELETED] = deleted_item
                
        except Exception as e:
            pass

    def populate_tree(self):
        prev = getattr(self, "current_category", None)
        self.tree.clear()
        self._path_items.clear()

        paths = db.fetch_categories()
        paths_sorted = sorted(paths, key=lambda p: (p == UNCATEGORIZED, p.count("/"), p.lower()))
        for p in paths_sorted:
            self._ensure_tree_item(p)

        self._add_special_folders()

        self._init_tree_view()

        if prev and prev in self._path_items:
            self.tree.setCurrentItem(self._path_items[prev])
            self.current_category = prev
        else:
            if UNCATEGORIZED in self._path_items:
                self.tree.setCurrentItem(self._path_items[UNCATEGORIZED])
                self.current_category = UNCATEGORIZED
            elif paths_sorted:
                self.tree.setCurrentItem(self._path_items[paths_sorted[0]])
                self.current_category = paths_sorted[0]

    def current_item_path(self, item: QTreeWidgetItem) -> str:
        path = item.data(0, Qt.UserRole)
        if path:
            return path
        segs = []
        it = item
        while it:
            segs.append(it.text(0))
            it = it.parent()
        return "/".join(reversed(segs)) if segs else UNCATEGORIZED

    def filter_by_category(self, item, column):
        try:
            self.search.blockSignals(True)
            self.search.clear()
        finally:
            self.search.blockSignals(False)
        
        category = self.current_item_path(item)
        self.current_category = category
        
        if category == self.SPECIAL_ARCHIVED:
            self._load_special_folder_entries("archived")
        elif category == self.SPECIAL_EXPIRED:
            self._load_special_folder_entries("expired")
        elif category == self.SPECIAL_DELETED:
            self._load_special_folder_entries("deleted")
        else:
            self.reload()

    def _load_special_folder_entries(self, status: str):
        try:
            rows = db.fetch_by_status(status)
            self._load_table(rows)
        except Exception as e:
            self.reload()

    def show_tree_menu(self, pos: QPoint):
        item = self.tree.itemAt(pos)
        
        if item and self._is_special_folder(item):
            menu = QMenu(self)
            
            if self.current_item_path(item) == self.SPECIAL_DELETED:
                menu.addAction("Empty Trash", self._empty_trash)
            elif self.current_item_path(item) in [self.SPECIAL_ARCHIVED, self.SPECIAL_DELETED]:
                menu.addAction("Restore All", lambda: self._restore_all_from_folder(item))
            
            if menu.actions():
                menu.exec(self.tree.viewport().mapToGlobal(pos))
            return
        
        menu = QMenu(self)
        if item:
            menu.addAction("Add Subfolder", lambda: self.add_subfolder(item))
            menu.addAction("Rename Folder", lambda: self.rename_folder(item))
            if self.current_item_path(item) != UNCATEGORIZED:
                menu.addAction("Delete Folder", lambda: self.delete_folder(item))
        else:
            menu.addAction("Add Folder", self.add_folder)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _empty_trash(self):
        try:
            deleted_entries = db.fetch_by_status("deleted")
            if not deleted_entries:
                QMessageBox.information(self, "Empty Trash", "Trash is already empty.")
                return
            
            reply = QMessageBox.warning(
                self, "Empty Trash",
                f"Permanently delete {len(deleted_entries)} item(s) from trash?\n\n"
                "This action cannot be undone!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                for row in deleted_entries:
                    entry_id = row[0]
                    db.permanently_delete_entry(entry_id)
                
                self.populate_tree()
                self.reload()
                self._log_status(f"Permanently deleted {len(deleted_entries)} item(s)", 2000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to empty trash:\n{e}")

    def _restore_all_from_folder(self, item: QTreeWidgetItem):
        folder_path = self.current_item_path(item)
        
        status_map = {
            self.SPECIAL_ARCHIVED: "archived",
            self.SPECIAL_DELETED: "deleted",
        }
        
        status = status_map.get(folder_path)
        if not status:
            return
        
        try:
            entries = db.fetch_by_status(status)
            if not entries:
                QMessageBox.information(self, "Restore All", "No items to restore.")
                return
            
            reply = QMessageBox.question(
                self, "Restore All",
                f"Restore {len(entries)} item(s) to active status?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                for row in entries:
                    entry_id = row[0]
                    db.restore_entry(entry_id)
                
                self.populate_tree()
                self.reload()
                self._log_status(f"Restored {len(entries)} item(s)", 2000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore items:\n{e}")

    def add_folder(self):
        name, ok = QInputDialog.getText(self, "Add Folder", "Folder name:")
        if ok:
            path = (name or "").strip()
            if not path:
                return
            if db.category_exists(path):
                QMessageBox.warning(self, "Error", f"A folder named '{path}' already exists.")
                return
            db.add_category(path)
            self.populate_tree()

    def add_subfolder(self, item: QTreeWidgetItem):
        parent_path = self.current_item_path(item)
        name, ok = QInputDialog.getText(self, "Add Subfolder", f"Subfolder under '{parent_path}':")
        if ok:
            name = (name or "").strip()
            if not name:
                return
            new_path = f"{parent_path}/{name}" if parent_path and parent_path != "/" else name
            if db.category_exists(new_path):
                QMessageBox.warning(self, "Error", f"A folder named '{name}' already exists.")
                return
            db.add_category(new_path)
            self.populate_tree()

    def rename_folder(self, item: QTreeWidgetItem):
        old = self.current_item_path(item)
        if old == UNCATEGORIZED:
            QMessageBox.information(self, "Not allowed", "You cannot rename 'Uncategorized'.")
            return
        
        if self._is_special_folder(item):
            QMessageBox.information(self, "Not allowed", "You cannot rename system folders.")
            return

        leaf = old.split("/")[-1]
        new_leaf, ok = QInputDialog.getText(self, "Rename Folder", "New name:", text=leaf)
        if ok:
            new_leaf = (new_leaf or "").strip()
            if not new_leaf or new_leaf == leaf:
                return
            parent = "/".join(old.split("/")[:-1])
            new_full = f"{parent}/{new_leaf}" if parent else new_leaf

            if db.category_exists(new_full):
                QMessageBox.warning(self, "Error", f"A folder named '{new_leaf}' already exists.")
                return

            try:
                db.rename_category(old, new_full)
            except ValueError as e:
                QMessageBox.warning(self, "Rename failed", str(e))
                return

            self.current_category = new_full
            self.populate_tree()
            self.reload()

    def delete_folder(self, item: QTreeWidgetItem):
        path = self.current_item_path(item)
        if path == UNCATEGORIZED:
            QMessageBox.information(self, "Not allowed", "You cannot delete 'Uncategorized'.")
            return
        
        if self._is_special_folder(item):
            QMessageBox.information(self, "Not allowed", "You cannot delete system folders.")
            return
            
        confirm = QMessageBox.question(
            self, "Confirm",
            f"Delete folder '{path}' and move its entries (including subfolders) to '{UNCATEGORIZED}'?"
        )
        if confirm == QMessageBox.Yes:
            db.delete_category(path)
            self.current_category = UNCATEGORIZED
            self.populate_tree()
            self.reload()

    def _rebuild_tree_preserving_selection(self, target_category: str | None = None):
        prev = getattr(self, "current_category", None)
        cat  = target_category if target_category is not None else prev

        try: self.tree.setUpdatesEnabled(False)
        except Exception: pass

        try:
            self.tree.clear()
            self._path_items.clear()
        except Exception:
            pass

        self.populate_tree()

        if cat and cat in self._path_items:
            try:
                self.tree.setCurrentItem(self._path_items[cat])
                self.current_category = cat
            except Exception:
                pass

        try:
            self.tree.setUpdatesEnabled(True)
            self.tree.viewport().update()
        except Exception:
            pass
