# region Imports
# external modules
import os

# blender modules
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty, IntProperty
from bpy.types import AddonPreferences
import rna_keymap_ui

# relative imports
from . import properties, functions, config, update, keymap
from .log import logger, log_sys
# endregion

__module__ = __package__.split(".")[0]

# region Preferences
class AR_preferences(AddonPreferences):
    bl_idname = __package__.split(".")[0]
    addon_directory : StringProperty(name= "addon directory", default= os.path.dirname(os.path.dirname(__file__)), get= lambda self: self.bl_rna.properties['addon_directory'].default)  # get the base addon directory
    prefernece_tab : EnumProperty(items=[
            ('settings', "Settings", ""),
            ('path', "Paths", ""),
            ('keymap', "Keymaps", ""),
            ('update', "Update", "")
        ],
        name= "Tab", description= "Switch between preferenc tabs"
    )

    # icon manager
    def get_icon_path(self) -> str:
        origin_path = self.get('icon_path', 'Fallback')
        if os.path.exists(origin_path):
            return self['icon_path']
        else:
            path = os.path.join(self.addon_directory, "Icons")
            if origin_path != 'Fallback':
                logger.error("ActRec ERROR: Storage Path \"" + origin_path +"\" don't exist, fallback to " + path)
            self['icon_path'] = path
            if not os.path.exists(path):
                os.makedirs(path)
            return path
    def set_icon_path(self, origin_path: str) -> None:
        self['icon_path'] = origin_path
        if not(os.path.exists(origin_path) and os.path.isdir(origin_path)):
            os.makedirs(origin_path)
    icon_path : StringProperty(name= "Icons Path", description= "The Path to the Storage for the added Icons", default= os.path.join(os.path.dirname(os.path.dirname(__file__)), "Storage.json"), get=get_icon_path, set=set_icon_path)
    selected_icon : IntProperty(name="selected icon", description= "only internal usage", default= 0, min= 0, options= {'HIDDEN'}) #Icon NONE: Global: BLANK1 (101), Local: MESH_PLANE (286)
    
    # update
    update : BoolProperty()
    restart : BoolProperty()
    version : StringProperty()
    auto_update : BoolProperty(default= True, name= "Auto Update", description= "automatically search for a new Update")
    update_progress : IntProperty(name= "Update Progress", default= -1, min= -1, max= 100, soft_min= 0, soft_max= 100, subtype= 'PERCENTAGE') # use as slider

    # locals
    local_actions : CollectionProperty(type= properties.AR_local_actions)

    def get_active_local_action_index(self):
        value = self.get('active_local_action_index', 0)
        actions_length = len(self.local_actions)
        return value if value < actions_length else actions_length - 1
    def set_active_local_action_index(self, value):
        AR = bpy.context.preferences.addons[__module__].preferences
        if not AR.local_record_macros:
            actions_length = len(self.local_actions)
            value = value if value < actions_length else actions_length - 1
            self['active_local_action_index'] = value if value >= 0 else actions_length - 1
    active_local_action_index : IntProperty(name= "Select", min= 0, get= get_active_local_action_index, set= set_active_local_action_index)

    local_to_global_mode : EnumProperty(items=[("copy", "Copy", "Copy the Action over to Global"), ("move", "Move", "Move the Action over to Global and Delete it from Local")], name= "Mode")
    local_record_macros : BoolProperty(name= "Record Macros", default= False)
    def hide_show_local_in_texteditor(self, context):
        if self.hide_local_text:
            for text in bpy.data.texts:
                if text.lines[0].body.strip().startswith("###AR###"):
                    bpy.data.texts.remove(text)
        else:
            for action in self.local_actions:
                functions.local_action_to_text(action)
    hide_local_text : BoolProperty(name= "Hide Local Action in Texteditor", description= "Hide the Local Action in the Texteditor", update= hide_show_local_in_texteditor)
    local_create_empty : BoolProperty(default= True, name= "Create Empty", description= "Create Empty Macro on Error")

    # macros
    last_macro_label : StringProperty(name= "last label", default= "label of the last macro")
    last_macro_command : StringProperty(name= "last command", default= "command of the last macro")

    operators_list_length : IntProperty(name= "INTERNAL")

    # globals
    global_actions : CollectionProperty(type= properties.AR_global_actions)

    global_to_local_mode : EnumProperty(items=[("copy", "Copy", "Copy the Action over to Global"), ("move", "Move", "Move the Action over to Global and Delete it from Local")], name= "Mode")
    autosave : BoolProperty(default= True, name= "Autosave", description= "automatically saves all Global Buttons to the Storage")
    global_rename : StringProperty(name= "Rename", description= "Rename the selected Action")
    global_hide_menu : BoolProperty(name= "Hide", description= "Hide the global Menu")

    import_settings : CollectionProperty(type= properties.AR_global_import_category)
    import_extension : StringProperty()

    # categories
    def get_storage_path(self) -> str:
        origin_path = self.get('storage_path', 'Fallback')
        if os.path.exists(origin_path):
            return self['storage_path']
        else:
            path = os.path.join(self.addon_directory, "Storage.json")
            if origin_path != 'Fallback':
                logger.error("ActRec ERROR: Storage Path \"" + origin_path +"\" don't exist, fallback to " + path)
            self['storage_path'] = path
            return path
    def set_storage_path(self, origin_path: str) -> None:
        self['storage_path'] = origin_path
        if not(os.path.exists(origin_path) and os.path.isfile(origin_path)):
            os.makedirs(os.path.dirname(origin_path))
            with open(origin_path, 'w') as storage_file:
                storage_file.write('{}')
    storage_path : StringProperty(name= "Stroage Path", description= "The Path to the Storage for the saved Categories", default= os.path.join(os.path.dirname(os.path.dirname(__file__)), "Storage.json"), get=get_storage_path, set=set_storage_path)

    categories : CollectionProperty(type= properties.AR_categories)
    def get_selected_category(self):
        return self.get("categories.selected_id", '')
    selected_category : StringProperty(get= get_selected_category, default= '')
    show_all_categories : BoolProperty(name= "Show All Categories", default= False)

    def draw(self, context):
        AR = context.preferences.addons[__module__].preferences
        layout = self.layout
        col = layout.column()
        row = col.row(align= True)
        row.prop(AR, 'prefernece_tab', expand= True)
        if AR.prefernece_tab == 'update':
            col.operator('wm.url_open', text= "Release Notes").url = config.config["releasNotes_URL"]
            row = col.row()
            if AR.update:
                update.draw_update_button(row, AR)
            else:
                row.operator('ar.update_check', text= "Check For Updates")
                if AR.restart:
                    row.operator('ar.show_restart_menu', text= "Restart to Finsih")
            if AR.version != '':
                if AR.update:
                    col.label(text= "A new Version is available (%s)" %AR.version)
                else:
                    col.label(text= "You are using the latest Vesion (%s)" %AR.version)
        elif AR.prefernece_tab == 'path':
            col.label(text= 'Action Storage Folder')
            row = col.row()
            ops = row.operator("ar.preferences_directory_selector", text= "Select Action Button’s Storage Folder", icon= 'FILEBROWSER')
            ops.pref_property = "storage_path"
            ops.path_extension = "Storage.json"
            ops = row.operator("ar.preferences_recover_directory", text= "Recover Default Folder", icon= 'FOLDER_REDIRECT')
            ops.pref_property = "storage_path"
            ops.path_extension = "Storage.json"
            box = col.box()
            box.label(text= self.storage_path)
            col.separator(factor= 1.5)
            row = col.row().split(factor= 0.5)
            row.label(text= "Icon Storage Folder")
            row2 = row.row(align= True).split(factor= 0.65, align= True)
            row2.operator("ar.add_custom_icon", text= "Add Custom Icon", icon= 'PLUS')
            row2.operator("ar.delete_custom_icon", text= "Delete", icon= 'TRASH')
            row = col.row()
            ops = row.operator("ar.preferences_directory_selector", text= "Select Icon Storage Folder", icon= 'FILEBROWSER')
            ops.pref_property = "icon_path"
            ops.path_extension = ""
            ops = row.operator("ar.preferences_recover_directory", text= "Recover Default Folder", icon= 'FOLDER_REDIRECT')
            ops.pref_property = "icon_path"
            ops.path_extension = ""
            box = col.box()
            box.label(text= self.icon_path)
            col.separator(factor= 1.5)
            col.operator('ar.preferences_open_explorer', text= "Open Log").path = log_sys.path
        elif AR.prefernece_tab == 'keymap':
            col2 = col.column()
            kc = bpy.context.window_manager.keyconfigs.user
            km = kc.keymaps['Screen']
            for item in keymap.keymaps['default'].keymap_items:
                kmi = km.keymap_items[item.idname]
                rna_keymap_ui.draw_kmi(kc.keymaps, kc, km, kmi, col2, 0)
        elif AR.prefernece_tab == 'settings':
            row = col.row()
            row.prop(self, 'auto_update')
            row.prop(self, 'autosave')
            row = col.row()
            row.prop(self, 'hide_local_text')
            row.prop(self, 'local_create_empty')
            col.separator(factor= 1.5)
            row = col.row()
            row.operator('wm.url_open', text= "Manual", icon= 'ASSET_MANAGER').url = config.config["Manual_URL"]
            row.operator('wm.url_open', text= "Hint", icon= 'HELP').url = config.config["Hint_URL"]
            row.operator('wm.url_open', text= "Bug Report", icon= 'URL').url = config.config["BugReport_URL"]
# endregion

classes = [
    AR_preferences
]

# region Registration
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion