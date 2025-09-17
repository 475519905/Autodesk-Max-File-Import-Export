# Blender addon to import/export 3ds Max (.max) files via FBX conversion
# Uses 3ds Max Python API through subprocess calls

bl_info = {
    "name": "Autodesk 3ds Max File Import-Export",
    "blender": (3, 0, 0),
    "category": "Import-Export",
    "version": (1, 0, 0),
    "author": "3ds Max Integration",
    "description": "Import and export Autodesk 3ds Max (.max) files via FBX intermediate conversion",
    "location": "File > Import/Export",
    "doc_url": "https://help.autodesk.com/view/3DSMAX/2022/ENU/",
    "support": "COMMUNITY",
}

import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator, AddonPreferences, FileHandler
from bpy_extras.io_utils import ExportHelper, ImportHelper
import os
import subprocess
import tempfile
import logging
import traceback
import winreg
import re

# Global constants
cache_dir = os.path.join(os.path.expanduser("~"), "Documents", "blender_3dsmax_cache")
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

# Logging setup
log_file = os.path.join(os.path.expanduser("~"), "Documents", "blender_3dsmax_log.txt")
log_dir = os.path.dirname(log_file)

try:
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
except Exception as e:
    print(f"Warning: Could not set up logging: {e}")
    import sys
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.INFO)

if log_dir and not os.path.exists(log_dir): # Log if creation might have been an issue
    logger.info(f"Log directory {log_dir} might not have been created if an error occurred earlier.")
else:
    logger.info(f"Logging to: {log_file}")

def detect_max_python_path():
    """Detect the highest version 3ds Max Python path through registry"""
    try:
        max_installations = {}
        
        # Check common registry paths
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Autodesk\3dsMax"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Autodesk\3dsMax"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Autodesk\3dsMax"),
        ]
        
        for hkey, base_path in registry_paths:
            try:
                with winreg.OpenKey(hkey, base_path) as key:
                    i = 0
                    while True:
                        try:
                            version_key = winreg.EnumKey(key, i)
                            # Match version number formats like "25.0", "26.0", "2025", "2026" etc.
                            version_match = re.match(r'^(\d+)(?:\.(\d+))?$', version_key)
                            if version_match:
                                # Handle different version number formats
                                if '.' in version_key:
                                    version_num = float(version_key)
                                else:
                                    # For year formats like "2025", convert to version number
                                    year = int(version_key)
                                    if year >= 2020:
                                        version_num = year - 2000  # 2025 -> 25.0
                                    else:
                                        version_num = float(version_key)
                                
                                try:
                                    with winreg.OpenKey(key, version_key) as ver_key:
                                        install_path, _ = winreg.QueryValueEx(ver_key, "Installdir")
                                        if install_path and os.path.exists(install_path):
                                            # Check multiple possible Python path locations
                                            python_paths = [
                                                os.path.join(install_path, "Python", "python.exe"),
                                                os.path.join(install_path, "bin", "python.exe"),
                                                os.path.join(install_path, "Python37", "python.exe"),
                                                os.path.join(install_path, "Python39", "python.exe"),
                                            ]
                                            
                                            for python_path in python_paths:
                                                if os.path.exists(python_path):
                                                    max_installations[version_num] = {
                                                        'path': install_path,
                                                        'python_path': python_path,
                                                        'version': version_key
                                                    }
                                                    logger.info(f"Found 3ds Max {version_key} at: {install_path}")
                                                    break
                                except Exception as e:
                                    logger.debug(f"Error reading version {version_key}: {e}")
                            i += 1
                        except OSError:
                            break
            except Exception as e:
                logger.debug(f"Error accessing registry path {base_path}: {e}")
        
        # Return the highest version Python path
        if max_installations:
            latest_version = max(max_installations.keys())
            latest_install = max_installations[latest_version]
            logger.info(f"Selected 3ds Max {latest_install['version']} (highest version found)")
            return latest_install['python_path']
        else:
            logger.warning("No 3ds Max installations found in registry")
            return ""
            
    except Exception as e:
        logger.error(f"Error detecting 3ds Max from registry: {e}")
        return ""

class PREFERENCES_OT_detect_max_python(Operator):
    """Auto-detect 3ds Max Python path"""
    bl_idname = "preferences.detect_max_python"
    bl_label = "Auto Detect"
    bl_description = "Automatically detect the highest version 3ds Max Python path from registry"
    
    def execute(self, context):
        preferences = context.preferences.addons[__name__].preferences
        detected_path = detect_max_python_path()
        
        if detected_path:
            preferences.max_python_path = detected_path
            self.report({'INFO'}, f"Detected 3ds Max Python path: {detected_path}")
            logger.info(f"Auto-detected 3ds Max Python path: {detected_path}")
        else:
            self.report({'WARNING'}, "No 3ds Max installation found. Please set path manually.")
            logger.warning("No 3ds Max installation detected")
        
        return {'FINISHED'}

class MaxPreferences(AddonPreferences):
    bl_idname = __name__

    max_python_path: StringProperty(
        name="3ds Max Python Path",
        description="Path to 3ds Max's Python executable (python.exe)",
        subtype='FILE_PATH',
        default="" # Will be auto-detected
    )
    
    def __init__(self):
        super().__init__()
        
    def draw_header(self, context):
        """Auto-detect path when preferences are first opened"""
        if not hasattr(self, '_auto_detected') and not self.max_python_path:
            detected_path = detect_max_python_path()
            if detected_path:
                self.max_python_path = detected_path
                logger.info(f"Auto-detected 3ds Max Python path on first open: {detected_path}")
            self._auto_detected = True
    
    # Import default settings
    default_import_models: BoolProperty(
        name="Default Import Models",
        description="Default import mesh objects",
        default=True
    )
    default_import_lights: BoolProperty(
        name="Default Import Lights",
        description="Default import light objects",
        default=True
    )
    default_import_cameras: BoolProperty(
        name="Default Import Cameras",
        description="Default import camera objects",
        default=True
    )
    default_import_splines: BoolProperty(
        name="Default Import Splines",
        description="Default import curve/spline objects",
        default=True
    )
    default_import_animations: BoolProperty(
        name="Default Import Animations",
        description="Default import and apply animations",
        default=True
    )
    default_import_materials: BoolProperty(
        name="Default Import Materials",
        description="Default assign materials to imported objects",
        default=True
    )
    default_import_armatures: BoolProperty(
        name="Default Import Armatures",
        description="Default import skeleton/bone structures",
        default=True
    )
    default_apply_rotation: BoolProperty(
        name="Default Apply X-Axis 180° Rotation",
        description="Default rotate imported objects 180 degrees around X-axis",
        default=False
    )
    default_apply_scale: BoolProperty(
        name="Default Apply 0.01 Scale",
        description="Default scale imported objects to 0.01 (shrink by 100x)",
        default=True
    )

    def draw(self, context):
        # Auto-detect path on first open
        self.draw_header(context)
        
        layout = self.layout
        
        # 3ds Max Python path setting
        path_row = layout.row(align=True)
        path_row.prop(self, "max_python_path")
        path_row.operator("preferences.detect_max_python", text="", icon='FILE_REFRESH')
        
        # Display detection status
        if self.max_python_path:
            if os.path.exists(self.max_python_path):
                status_row = layout.row()
                status_row.label(text="✓ Path Valid", icon='CHECKMARK')
            else:
                status_row = layout.row()
                status_row.label(text="✗ Path Invalid", icon='ERROR')
        else:
            detect_row = layout.row()
            detect_row.operator("preferences.detect_max_python", text="Auto Detect 3ds Max Python Path", icon='FILE_REFRESH')
        
        # Information hint
        info_box = layout.box()
        info_box.label(text="Uses 3ds Max Python to call MAXScript for file conversion", icon='INFO')
        
        layout.separator()
        
        # Import Default Settings
        import_box = layout.box()
        import_box.label(text="Import Default Settings", icon='IMPORT')
        
        import_col = import_box.column(align=True)
        import_grid = import_col.grid_flow(columns=2, align=True)
        import_grid.prop(self, "default_import_models", icon='MESH_DATA')
        import_grid.prop(self, "default_import_lights", icon='LIGHT')
        import_grid.prop(self, "default_import_cameras", icon='CAMERA_DATA')
        import_grid.prop(self, "default_import_splines", icon='CURVE_DATA')
        import_grid.prop(self, "default_import_animations", icon='ANIM')
        import_grid.prop(self, "default_import_materials", icon='MATERIAL')
        import_grid.prop(self, "default_import_armatures", icon='ARMATURE_DATA')
        import_col.prop(self, "default_apply_rotation", icon='CON_ROTLIKE')
        import_col.prop(self, "default_apply_scale", icon='CON_SIZELIKE')


class ExportMax(Operator, ExportHelper):
    bl_idname = "export_scene.max"
    bl_label = "Export 3ds Max File"
    bl_description = "Export scene to Autodesk 3ds Max (.max) format via FBX intermediate conversion"
    
    filename_ext = ".max"
    filter_glob: StringProperty(default="*.max", options={'HIDDEN'})
    
    # Export filters - similar to Maya plugin
    export_models: BoolProperty(name="Models", description="Export mesh objects", default=True)
    export_lights: BoolProperty(name="Lights", description="Export light objects", default=True)
    export_cameras: BoolProperty(name="Cameras", description="Export camera objects", default=True)
    export_splines: BoolProperty(name="Splines", description="Export curve/spline objects", default=True)
    export_animations: BoolProperty(name="Animations", description="Export animations", default=True)
    
    use_selection: BoolProperty(
        name="Selection Only",
        description="Export selected objects only",
        default=False
    )

    def draw(self, context):
        layout = self.layout
        
        # Export options
        col = layout.column(align=True)
        col.label(text="Export Options:")
        grid = layout.grid_flow(columns=2, align=True)
        grid.prop(self, "export_models", icon='MESH_DATA', toggle=True)
        grid.prop(self, "export_lights", icon='LIGHT', toggle=True)
        grid.prop(self, "export_cameras", icon='CAMERA_DATA', toggle=True)
        grid.prop(self, "export_splines", icon='CURVE_DATA', toggle=True)
        grid.prop(self, "export_animations", icon='ANIM', toggle=True)
        
        layout.separator()
        layout.prop(self, "use_selection")
    
    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "No filepath specified")
            return {'CANCELLED'}
        
        # Ensure .max extension
        if not self.filepath.lower().endswith('.max'):
            base_path = os.path.splitext(self.filepath)[0]
            final_filepath = base_path + '.max'
        else:
            final_filepath = self.filepath
        
        # Ensure consistent path separators and no double extension
        final_filepath = os.path.normpath(final_filepath)
        if final_filepath.lower().endswith('.max.max'):
            base_path = final_filepath[:-4]  # Remove the last .max
            final_filepath = base_path + '.max'
            
        logger.info(f"Initiating 3ds Max export operation. Output: {final_filepath}")
        return self.export_max(context, final_filepath)

    def export_max(self, context, filepath):
        preferences = context.preferences.addons[__name__].preferences
        max_python_path = preferences.max_python_path

        if not max_python_path or not os.path.exists(max_python_path):
            logger.error(f"3ds Max Python executable not found at: {max_python_path}. Please set it in Addon Preferences.")
            self.report({'ERROR'}, "3ds Max Python executable path not set or invalid. Check Addon Preferences.")
            return {'CANCELLED'}

        with tempfile.TemporaryDirectory(prefix="blender_maya_export_") as temp_dir:
            fbx_path = os.path.join(temp_dir, "temp_export.fbx")
            logger.info(f"Intermediate FBX will be exported to: {fbx_path}")
            
            # Apply export filters and get objects to export
            try:
                original_selection = bpy.context.selected_objects[:]
                original_active = bpy.context.view_layer.objects.active
                
                bpy.ops.object.select_all(action='DESELECT')
                export_objects_count = 0
                
                # Determine source objects based on selection mode
                if self.use_selection:
                    source_objects = bpy.context.selected_objects if original_selection else []
                else:
                    source_objects = bpy.context.scene.objects
                
                for obj in source_objects:
                    # Check if object is in current view layer before trying to select it
                    if obj.name not in bpy.context.view_layer.objects:
                        continue
                    
                    obj.select_set(False) 
                    should_select = False
                    if obj.type == 'MESH' and self.export_models: should_select = True
                    elif obj.type == 'LIGHT' and self.export_lights: should_select = True
                    elif obj.type == 'CAMERA' and self.export_cameras: should_select = True
                    elif obj.type == 'CURVE' and self.export_splines: should_select = True
                    elif obj.type == 'ARMATURE' and (self.export_models or self.export_animations): should_select = True
                    
                    if should_select:
                        obj.select_set(True)
                        export_objects_count += 1
                
                if export_objects_count == 0:
                    self.report({'WARNING'}, "No objects match export filters. Nothing exported to FBX.")
                    logger.warning("No objects matched export filters for FBX export.")
                    # Restore selection before returning
                    bpy.ops.object.select_all(action='DESELECT')
                    if original_active and original_active.name in bpy.context.view_layer.objects:
                        bpy.context.view_layer.objects.active = original_active
                    for obj_ref in original_selection:
                        if obj_ref and obj_ref.name in bpy.context.view_layer.objects: 
                            obj_ref.select_set(True)
                    return {'CANCELLED'}

                logger.info(f"Exporting {export_objects_count} objects to FBX based on filters.")
            
                # Export to FBX first
                bpy.ops.export_scene.fbx(
                    filepath=fbx_path,
                    use_selection=True,  # Always use selection since we've filtered objects
                    global_scale=1.0,
                    apply_unit_scale=True,
                    apply_scale_options='FBX_SCALE_NONE',
                    object_types={'MESH', 'CURVE', 'ARMATURE', 'EMPTY', 'CAMERA', 'LIGHT'},
                    use_mesh_modifiers=True,
                    mesh_smooth_type='EDGE',
                    use_subsurf=False,
                    use_mesh_edges=False,
                    use_tspace=False,
                    use_custom_props=False,
                    add_leaf_bones=True,
                    primary_bone_axis='Y',
                    secondary_bone_axis='X',
                    use_armature_deform_only=False,
                    armature_nodetype='NULL',
                    bake_anim=self.export_animations,
                    bake_anim_use_all_bones=True,
                    bake_anim_use_nla_strips=True,
                    bake_anim_use_all_actions=True,
                    bake_anim_force_startend_keying=True,
                    bake_anim_step=1.0,
                    bake_anim_simplify_factor=1.0,
                    path_mode='COPY',  # Copy textures
                    embed_textures=False,
                    batch_mode='OFF',
                    use_batch_own_dir=True,
                    use_metadata=True
                )
                
                # Restore original Blender selection
                bpy.ops.object.select_all(action='DESELECT')
                if original_active and original_active.name in bpy.context.view_layer.objects:
                    bpy.context.view_layer.objects.active = original_active
                for obj_ref in original_selection:
                    if obj_ref and obj_ref.name in bpy.context.view_layer.objects: 
                        obj_ref.select_set(True)
                
                if not os.path.exists(fbx_path) or os.path.getsize(fbx_path) == 0:
                    raise Exception("FBX export failed or resulted in empty file")
                
                logger.info("FBX export from Blender completed.")
            except Exception as e:
                logger.error(f"FBX export from Blender failed: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.report({'ERROR'}, f"FBX export from Blender failed. See log: {log_file}")
                return {'CANCELLED'}

            # Generate simple MAXScript calling script
            max_script = self._generate_simple_script(fbx_path, filepath)
            max_script_path = os.path.join(temp_dir, "blender_to_max_export_script.py")
            with open(max_script_path, 'w', encoding='utf-8') as f:
                f.write(max_script)

            logger.info(f"Running 3ds Max script for final export: {max_script_path}")
            try:
                # Basic environment for 3ds Max Python
                run_env = os.environ.copy() 
                max_bin_dir = os.path.dirname(max_python_path)
                max_root_dir = os.path.dirname(max_bin_dir) if max_bin_dir else os.path.dirname(max_python_path)
                run_env['ADSK_3DSMAX_x64_2026'] = max_root_dir
                run_env['PATH'] = f"{max_bin_dir}{os.pathsep}{run_env.get('PATH', '')}"

                # Use Python to run the script
                result = subprocess.run([max_python_path, max_script_path], 
                                     check=False, # Check manually
                                     capture_output=True, 
                                     text=True,
                                     env=run_env,
                                     encoding='utf-8')
                
                stdout_msg = result.stdout.strip() if result.stdout else ""
                stderr_msg = result.stderr.strip() if result.stderr else ""
                
                if stdout_msg: logger.info(f"3ds Max Export Script STDOUT:\n{stdout_msg}")
                if stderr_msg: logger.error(f"3ds Max Export Script STDERR:\n{stderr_msg}")
                
                if result.returncode != 0:
                    logger.error(f"Running 3ds Max export script failed. RC: {result.returncode}")
                    self.report({'ERROR'}, f"3ds Max script execution failed (RC: {result.returncode}). See log: {log_file}")
                    return {'CANCELLED'}
                
            except Exception as e_run_script:
                logger.error(f"Error running 3ds Max export script: {str(e_run_script)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.report({'ERROR'}, f"Failed to run 3ds Max script. See log: {log_file}")
                return {'CANCELLED'}

        logger.info(f"Export to 3ds Max file completed: {filepath}")
        self.report({'INFO'}, f"Exported successfully to: {filepath}")
        return {'FINISHED'}
    
    def _generate_simple_script(self, fbx_path, target_path):
        """Generate simple Python script to call MAXScript"""
        return f"""
import os
import sys
import subprocess
import tempfile

def print_and_flush(message):
    print(message)
    sys.stdout.flush()
    sys.stderr.flush()

print_and_flush("[MAX_EXPORT_LOG] 3ds Max Script Start (Export Process)")

fbx_to_import = r"{fbx_path}"
target_max_file = r"{target_path}"

print_and_flush(f"[MAX_EXPORT_LOG] Processing FBX: {{fbx_to_import}}")

if not os.path.exists(fbx_to_import):
    print_and_flush(f"[MAX_EXPORT_ERROR] FBX file not found: {{fbx_to_import}}")
    sys.exit(1)

try:
    # Find 3dsmaxbatch.exe from Python path
    max_python_dir = os.path.dirname(sys.executable)
    max_root = os.path.dirname(max_python_dir)
    max_batch = os.path.join(max_root, "3dsmaxbatch.exe")
    
    if not os.path.exists(max_batch):
        print_and_flush(f"[MAX_EXPORT_ERROR] 3dsmaxbatch.exe not found at: {{max_batch}}")
        sys.exit(1)
    
    print_and_flush(f"[MAX_EXPORT_LOG] Using 3dsmaxbatch.exe: {{max_batch}}")
    
    # Create MaxScript content
    maxscript_content = '''
resetMaxFile #noPrompt
importFile @"''' + fbx_to_import.replace(os.sep, '/') + '''" #noPrompt
saveMaxFile @"''' + target_max_file.replace(os.sep, '/') + '''" quiet:true
quitMax exitCode:0
'''
    
    # Write temporary MaxScript file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ms', delete=False, encoding='utf-8') as f:
        f.write(maxscript_content)
        script_path = f.name
    
    print_and_flush(f"[MAX_EXPORT_LOG] Created MaxScript: {{script_path}}")
    
    try:
        # Execute 3dsmaxbatch with the script
        result = subprocess.run([max_batch, script_path], 
                              capture_output=True, text=True, encoding='utf-8', timeout=300)
        
        print_and_flush(f"[MAX_EXPORT_LOG] 3dsmaxbatch executed with return code: {{result.returncode}}")
        
        if result.stdout:
            print_and_flush(f"[MAX_EXPORT_LOG] STDOUT: {{result.stdout}}")
        if result.stderr:
            print_and_flush(f"[MAX_EXPORT_LOG] STDERR: {{result.stderr}}")
        
        if os.path.exists(target_max_file) and os.path.getsize(target_max_file) > 0:
            print_and_flush(f"[MAX_EXPORT_LOG] Successfully exported to 3ds Max (.MAX) format.")
        else:
            print_and_flush(f"[MAX_EXPORT_ERROR] Target 3ds Max file not created or empty: {{target_max_file}}")
            sys.exit(1)
    
    finally:
        try:
            os.unlink(script_path)
        except:
            pass
            
except subprocess.TimeoutExpired:
    print_and_flush(f"[MAX_EXPORT_ERROR] 3dsmaxbatch execution timed out")
    sys.exit(1)
except Exception as e:
    print_and_flush(f"[MAX_EXPORT_ERROR] Error during conversion: {{str(e)}}")
    sys.exit(1)

print_and_flush("[MAX_EXPORT_LOG] 3ds Max Script End (Export Process)")
"""


class ImportMax(Operator, ImportHelper):
    bl_idname = "import_scene.max"
    bl_label = "Import 3ds Max File"
    bl_description = "Import a 3ds Max (.max) file via FBX conversion"
    
    filename_ext = ".max"
    filter_glob: StringProperty(default="*.max", options={'HIDDEN'})
    
    # Import options - will use preferences defaults
    import_models: BoolProperty(name="Models", description="Import mesh objects")
    import_lights: BoolProperty(name="Lights", description="Import light objects")
    import_cameras: BoolProperty(name="Cameras", description="Import camera objects")
    import_splines: BoolProperty(name="Splines", description="Import curve/spline objects")
    import_animations: BoolProperty(name="Animations", description="Import and apply animations")
    import_materials: BoolProperty(name="Materials", description="Assign materials to imported objects")
    import_armatures: BoolProperty(name="Armatures", description="Import skeleton/bone structures")
    apply_rotation: BoolProperty(name="Apply X-Axis 180° Rotation", description="Rotate imported objects 180 degrees around X-axis")
    apply_scale: BoolProperty(name="Apply 0.01 Scale", description="Scale imported objects to 0.01 (shrink by 100x)")

    def invoke(self, context, event):
        # Set defaults from preferences
        preferences = context.preferences.addons[__name__].preferences
        self.import_models = preferences.default_import_models
        self.import_lights = preferences.default_import_lights
        self.import_cameras = preferences.default_import_cameras
        self.import_splines = preferences.default_import_splines
        self.import_animations = preferences.default_import_animations
        self.import_materials = preferences.default_import_materials
        self.import_armatures = preferences.default_import_armatures
        self.apply_rotation = preferences.default_apply_rotation
        self.apply_scale = preferences.default_apply_scale
        return super().invoke(context, event)

    def draw(self, context):
        layout = self.layout
        grid = layout.grid_flow(columns=2, align=True)
        grid.prop(self, "import_models", icon='MESH_DATA', toggle=True)
        grid.prop(self, "import_lights", icon='LIGHT', toggle=True)
        grid.prop(self, "import_cameras", icon='CAMERA_DATA', toggle=True)
        grid.prop(self, "import_splines", icon='CURVE_DATA', toggle=True)
        grid.prop(self, "import_animations", icon='ANIM', toggle=True)
        grid.prop(self, "import_materials", icon='MATERIAL', toggle=True)
        grid.prop(self, "import_armatures", icon='ARMATURE_DATA', toggle=True)
        layout.prop(self, "apply_rotation")
        layout.prop(self, "apply_scale")

    def execute(self, context):
        max_file_path = self.filepath
        logger.info(f"Initiating 3ds Max import for: {max_file_path}")

        if not max_file_path or not max_file_path.lower().endswith(".max"):
            self.report({'ERROR'}, "Invalid file path or extension. Must be .max")
            return {'CANCELLED'}

        preferences = context.preferences.addons[__name__].preferences
        max_python_path = preferences.max_python_path
        
        if not max_python_path or not os.path.exists(max_python_path):
            logger.error(f"3ds Max Python executable not found: {max_python_path}. Check Addon Preferences.")
            self.report({'ERROR'}, "3ds Max Python executable not found. Check Addon Preferences.")
            return {'CANCELLED'}

        base_name_ext = os.path.basename(max_file_path)
        base_name, _ = os.path.splitext(base_name_ext)
        fbx_file_name = f"blender_max_import_{base_name}.fbx"
        fbx_file_path = os.path.join(cache_dir, fbx_file_name)

        existing_object_names = {obj.name for obj in bpy.context.scene.objects}
        
        max_bin_path = os.path.dirname(max_python_path)
        max_location = os.path.dirname(max_bin_path)

        max_env = os.environ.copy()
        max_env["ADSK_3DSMAX_x64_2026"] = max_location
        max_env["PATH"] = f"{max_bin_path}{os.pathsep}{max_env.get('PATH', '')}"
        python_site_packages = os.path.join(max_location, 'Python', 'Lib', 'site-packages')
        if os.path.exists(python_site_packages):
            max_env["PYTHONPATH"] = f"{python_site_packages}{os.pathsep}{max_env.get('PYTHONPATH', '')}"
        max_plugin_path = os.path.join(max_location, 'plugins')
        max_script_path = os.path.join(max_location, 'scripts')
            
        max_env["ADSK_3DSMAX_PLUGINS_PATH"] = max_plugin_path
        max_env["ADSK_3DSMAX_SCRIPTS_PATH"] = max_script_path
        max_env["PYTHONIOENCODING"] = "UTF-8"

        # Generate simple import script
        max_import_script_content = self._generate_simple_import_script(max_file_path, fbx_file_path)
        
        temp_script_path = os.path.join(cache_dir, "temp_max_to_fbx_for_blender_import.py")
        with open(temp_script_path, 'w', encoding='utf-8') as f: f.write(max_import_script_content)
        
        logger.info(f"Executing 3ds Max to FBX conversion script: {temp_script_path}")
        try:
            result_max = subprocess.run(
                [max_python_path, temp_script_path], capture_output=True, text=True,
                encoding='utf-8', env=max_env, check=False
            )
            s_out = result_max.stdout.strip() if result_max.stdout else ""
            s_err = result_max.stderr.strip() if result_max.stderr else ""
            if s_out: logger.info(f"3ds Max->FBX Script STDOUT:\n{s_out}")
            if s_err: logger.error(f"3ds Max->FBX Script STDERR:\n{s_err}")

            if result_max.returncode != 0:
                logger.error(f"3ds Max to FBX script failed. RC: {result_max.returncode}")
                self.report({'ERROR'}, f"3ds Max conversion failed (RC: {result_max.returncode}). See log: {log_file}")
                return {'CANCELLED'}

        except Exception as e:
            logger.error(f"Failed to execute 3ds Max script: {str(e)}\n{traceback.format_exc()}")
            self.report({'ERROR'}, f"Failed to execute 3ds Max script: {str(e)}. See log: {log_file}")
            return {'CANCELLED'}

        # Import the FBX file into Blender
        if not os.path.exists(fbx_file_path):
            self.report({'ERROR'}, f"FBX conversion failed: {fbx_file_path} not found")
            return {'CANCELLED'}

        try:
            logger.info(f"Importing generated FBX into Blender: {fbx_file_path}")
            bpy.ops.object.select_all(action='DESELECT')
            
            # Remember pre-import object names for filtering
            existing_object_names = {obj.name for obj in bpy.context.scene.objects}
            
            # Import FBX
            bpy.ops.import_scene.fbx(
                filepath=fbx_file_path,
                global_scale=1.0,  # Use 1.0 scale, will apply 0.01 scale later
                use_custom_normals=True,
                use_image_search=True,
                use_alpha_decals=False,
                decal_offset=0.0,
                use_anim=self.import_animations,
                anim_offset=1.0,
                use_subsurf=False,
                use_custom_props=True,
                use_custom_props_enum_as_string=True,
                ignore_leaf_bones=False,
                force_connect_children=False,
                automatic_bone_orientation=False,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                use_prepost_rot=True
            )
            logger.info("FBX imported into Blender.")

            # Get imported objects
            imported_objects = {obj for obj in bpy.context.scene.objects if obj.name not in existing_object_names}
            logger.info(f"Identified {len(imported_objects)} newly imported Blender objects.")

            if imported_objects:
                bpy.ops.object.select_all(action='DESELECT')
                active_set = False
                for obj in imported_objects:
                    obj.select_set(True)
                    if not active_set:
                        bpy.context.view_layer.objects.active = obj
                        active_set = True
                
                # Apply rotation if requested
                if self.apply_rotation:
                    for obj in imported_objects:
                        obj.rotation_euler.x = 3.14159  # 180 degrees = π radians
                    logger.info("Applied X-axis 180 degree rotation.")
                
                # Apply 0.01 scale (shrink by 100x) to all imported objects if requested
                if self.apply_scale:
                    for obj in imported_objects:
                        obj.scale = (0.01, 0.01, 0.01)
                    logger.info("Applied 0.01 scale (shrunk by 100x).")
                
                bpy.ops.object.select_all(action='DESELECT')

                # Asset Filtering - similar to Maya plugin structure
                processed_for_deletion = set()
                if not self.import_models: 
                    processed_for_deletion.update(self._filter_objects_by_type(imported_objects, 'MESH', keep=False))
                if not self.import_lights: 
                    processed_for_deletion.update(self._filter_objects_by_type(imported_objects, 'LIGHT', keep=False))
                if not self.import_cameras: 
                    processed_for_deletion.update(self._filter_objects_by_type(imported_objects, 'CAMERA', keep=False))
                if not self.import_splines: 
                    processed_for_deletion.update(self._filter_objects_by_type(imported_objects, 'CURVE', keep=False))
                # Consider Armatures with models:
                if not self.import_armatures:
                    processed_for_deletion.update(self._filter_objects_by_type(imported_objects, 'ARMATURE', keep=False))
                elif not self.import_models and self.import_animations:
                    logger.info("Models are off, but animations are on. Armatures will be kept if present.")

                remaining_after_deletion = imported_objects - processed_for_deletion
                if not self.import_animations and remaining_after_deletion:
                    self._filter_animations_from_objects(remaining_after_deletion, keep=False)
                if not self.import_materials and remaining_after_deletion:
                    self._filter_materials_from_objects(remaining_after_deletion, keep=False)
            
            bpy.ops.object.select_all(action='DESELECT')

            # Clean up FBX file
            try: os.remove(fbx_file_path)
            except: pass

            self.report({'INFO'}, f"Successfully imported 3ds Max file: {os.path.basename(max_file_path)}")
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"FBX import to Blender failed: {str(e)}\n{traceback.format_exc()}")
            self.report({'ERROR'}, f"FBX import failed: {str(e)}. See log: {log_file}")
            return {'CANCELLED'}

    def _filter_objects_by_type(self, objects_to_check, obj_type, keep=True):
        bpy.ops.object.select_all(action='DESELECT')
        targeted_objects = set()
        for obj in objects_to_check:
            if obj and obj.name in bpy.context.scene.objects and obj.type == obj_type:
                obj.select_set(True)
                targeted_objects.add(obj)
        
        if not keep and targeted_objects:
            logger.info(f"Filtering: Deleting {len(targeted_objects)} objects of type {obj_type}.")
            bpy.ops.object.delete()
            return targeted_objects # Return what was deleted
        elif keep and targeted_objects:
             logger.info(f"Filtering: Keeping {len(targeted_objects)} objects of type {obj_type}.")
        bpy.ops.object.select_all(action='DESELECT')
        return targeted_objects if not keep else set() # Return deleted if not keep, else empty set

    def _filter_armatures_from_objects(self, objects_to_check, keep=True):
        if not keep:
            cleared_count = 0
            for obj in objects_to_check:
                if obj and obj.name in bpy.context.scene.objects and obj.type == 'ARMATURE':
                    bpy.data.objects.remove(obj)
                    cleared_count += 1
            if cleared_count > 0: logger.info(f"Filtering: Removed {cleared_count} armatures.")

    def _filter_animations_from_objects(self, objects_to_check, keep=True):
        if not keep:
            cleared_count = 0
            for obj in objects_to_check:
                if obj and obj.name in bpy.context.scene.objects and obj.animation_data:
                    obj.animation_data_clear()
                    cleared_count += 1
            if cleared_count > 0: logger.info(f"Filtering: Cleared animation data from {cleared_count} objects.")

    def _filter_materials_from_objects(self, objects_to_check, keep=True):
        if not keep:
            cleared_count = 0
            for obj in objects_to_check:
                if obj and obj.name in bpy.context.scene.objects and obj.data and hasattr(obj.data, 'materials'):
                    if obj.data.materials: obj.data.materials.clear(); cleared_count += 1
            if cleared_count > 0: logger.info(f"Filtering: Cleared material slots from {cleared_count} objects.")
    
    def _generate_simple_import_script(self, max_file_path, fbx_file_path):
        """Generate simple Python script to call MAXScript for import"""
        return f"""
import os
import sys
import subprocess
import tempfile

def print_and_flush(message):
    print(message)
    sys.stdout.flush()
    sys.stderr.flush()

print_and_flush("[MAX_IMPORT_LOG] 3ds Max Script Start (Import Process)")

max_input_path = r"{max_file_path}"
fbx_output_path = r"{fbx_file_path}"

print_and_flush(f"[MAX_IMPORT_LOG] Source: {{max_input_path}}, Target FBX: {{fbx_output_path}}")

if not os.path.exists(max_input_path):
    print_and_flush(f"[MAX_IMPORT_ERROR] Input 3ds Max file not found: {{max_input_path}}")
    sys.exit(1)

try:
    # Find 3dsmaxbatch.exe from Python path
    max_python_dir = os.path.dirname(sys.executable)
    max_root = os.path.dirname(max_python_dir)
    max_batch = os.path.join(max_root, "3dsmaxbatch.exe")
    
    if not os.path.exists(max_batch):
        print_and_flush(f"[MAX_IMPORT_ERROR] 3dsmaxbatch.exe not found at: {{max_batch}}")
        sys.exit(1)
    
    print_and_flush(f"[MAX_IMPORT_LOG] Using 3dsmaxbatch.exe: {{max_batch}}")

    # Create MAXScript file
    maxscript_content = '''
loadMaxFile @"''' + max_input_path.replace(os.sep, '/') + '''" quiet:true
exportFile @"''' + fbx_output_path.replace(os.sep, '/') + '''" #noPrompt selectedOnly:false
quitMax exitCode:0
'''

    # Write temporary MAXScript file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ms', delete=False, encoding='utf-8') as f:
        f.write(maxscript_content)
        script_path = f.name
    
    print_and_flush(f"[MAX_IMPORT_LOG] Created MaxScript: {{script_path}}")

    try:
        # Execute 3dsmaxbatch with the script
        result = subprocess.run([max_batch, script_path], 
                              capture_output=True, text=True, encoding='utf-8', timeout=300)
        
        print_and_flush(f"[MAX_IMPORT_LOG] 3dsmaxbatch executed with return code: {{result.returncode}}")
        
        if result.stdout:
            print_and_flush(f"[MAX_IMPORT_LOG] STDOUT: {{result.stdout}}")
        if result.stderr:
            print_and_flush(f"[MAX_IMPORT_LOG] STDERR: {{result.stderr}}")
        
        if os.path.exists(fbx_output_path) and os.path.getsize(fbx_output_path) > 0:
            file_size = os.path.getsize(fbx_output_path)
            print_and_flush(f"[MAX_IMPORT_LOG] FBX file exported: {{fbx_output_path}} (Size: {{file_size}} B)")
        else:
            print_and_flush(f"[MAX_IMPORT_ERROR] FBX export failed or file is empty: {{fbx_output_path}}")
            sys.exit(1)
    
    finally:
        try:
            os.unlink(script_path)
        except:
            pass
            
except subprocess.TimeoutExpired:
    print_and_flush(f"[MAX_IMPORT_ERROR] 3dsmaxbatch execution timed out")
    sys.exit(1)
except Exception as e:
    print_and_flush(f"[MAX_IMPORT_ERROR] Error during conversion: {{str(e)}}")
    sys.exit(1)

print_and_flush("[MAX_IMPORT_LOG] 3ds Max Script End (Import Process)")
"""


class InvokeExportMax(Operator):
    bl_idname = "invoke_export_scene.max"
    bl_label = "Export 3ds Max File Options"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(subtype='FILE_PATH')
    # Export filters - matching the main ExportMax class
    export_models: BoolProperty(name="Models", description="Export mesh objects", default=True)
    export_lights: BoolProperty(name="Lights", description="Export light objects", default=True)
    export_cameras: BoolProperty(name="Cameras", description="Export camera objects", default=True)
    export_splines: BoolProperty(name="Splines", description="Export curve/spline objects", default=True)
    export_animations: BoolProperty(name="Animations", description="Export animations", default=True)
    use_selection: BoolProperty(name="Selection Only", description="Export selected objects only", default=False)

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = "untitled.max"
        logger.info(f"Opening export options dialog for 3ds Max file: {self.filepath}")
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        
        # Export options
        col = layout.column(align=True)
        col.label(text="Export Options:")
        grid = layout.grid_flow(columns=2, align=True)
        grid.prop(self, "export_models", icon='MESH_DATA', toggle=True)
        grid.prop(self, "export_lights", icon='LIGHT', toggle=True)
        grid.prop(self, "export_cameras", icon='CAMERA_DATA', toggle=True)
        grid.prop(self, "export_splines", icon='CURVE_DATA', toggle=True)
        grid.prop(self, "export_animations", icon='ANIM', toggle=True)
        
        layout.separator()
        layout.prop(self, "use_selection")

    def execute(self, context):
        logger.info(f"Executing 3ds Max export for: {self.filepath} with options.")
        try:
            return bpy.ops.export_scene.max(
                'EXEC_DEFAULT', filepath=self.filepath,
                export_models=self.export_models, export_lights=self.export_lights,
                export_cameras=self.export_cameras, export_splines=self.export_splines,
                export_animations=self.export_animations, use_selection=self.use_selection
            )
        except Exception as e:
            logger.error(f"Export options export_scene.max call failed: {e}\n{traceback.format_exc()}")
            self.report({'ERROR'}, f"3ds Max export failed: {e}. See log.")
            return {'CANCELLED'}


class InvokeImportMax(Operator):
    bl_idname = "invoke_import_scene.max"
    bl_label = "Import 3ds Max File Options"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(subtype='FILE_PATH')
    # Import options - will use preferences defaults
    import_models: BoolProperty(name="Models", description="Import mesh objects")
    import_lights: BoolProperty(name="Lights", description="Import light objects")
    import_cameras: BoolProperty(name="Cameras", description="Import camera objects")
    import_splines: BoolProperty(name="Splines", description="Import curve/spline objects")
    import_animations: BoolProperty(name="Animations", description="Import and apply animations")
    import_materials: BoolProperty(name="Materials", description="Assign materials to imported objects")
    import_armatures: BoolProperty(name="Armatures", description="Import skeleton/bone structures")
    apply_rotation: BoolProperty(name="Apply X-Axis 180° Rotation", description="Rotate imported objects 180 degrees around X-axis")
    apply_scale: BoolProperty(name="Apply 0.01 Scale", description="Scale imported objects to 0.01 (shrink by 100x)")

    def invoke(self, context, event):
        if not self.filepath or not os.path.exists(self.filepath) or \
           not self.filepath.lower().endswith(".max"):
            self.report({'ERROR'}, "Invalid 3ds Max file (.max) for drag-and-drop.")
            return {'CANCELLED'}
        
        # Set defaults from preferences
        preferences = context.preferences.addons[__name__].preferences
        self.import_models = preferences.default_import_models
        self.import_lights = preferences.default_import_lights
        self.import_cameras = preferences.default_import_cameras
        self.import_splines = preferences.default_import_splines
        self.import_animations = preferences.default_import_animations
        self.import_materials = preferences.default_import_materials
        self.import_armatures = preferences.default_import_armatures
        self.apply_rotation = preferences.default_apply_rotation
        self.apply_scale = preferences.default_apply_scale
        
        logger.info(f"Drag-and-drop for 3ds Max file: {self.filepath}. Opening options dialog.")
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        grid = layout.grid_flow(columns=2, align=True)
        grid.prop(self, "import_models", icon='MESH_DATA', toggle=True)
        grid.prop(self, "import_lights", icon='LIGHT', toggle=True)
        grid.prop(self, "import_cameras", icon='CAMERA_DATA', toggle=True)
        grid.prop(self, "import_splines", icon='CURVE_DATA', toggle=True)
        grid.prop(self, "import_animations", icon='ANIM', toggle=True)
        grid.prop(self, "import_materials", icon='MATERIAL', toggle=True)
        grid.prop(self, "import_armatures", icon='ARMATURE_DATA', toggle=True)
        layout.prop(self, "apply_rotation")
        layout.prop(self, "apply_scale")

    def execute(self, context):
        logger.info(f"Executing 3ds Max import for: {self.filepath} (drag-and-drop) with options.")
        try:
            return bpy.ops.import_scene.max(
                'EXEC_DEFAULT', filepath=self.filepath,
                import_models=self.import_models, import_lights=self.import_lights,
                import_cameras=self.import_cameras, import_splines=self.import_splines,
                import_animations=self.import_animations, import_materials=self.import_materials,
                import_armatures=self.import_armatures, apply_rotation=self.apply_rotation,
                apply_scale=self.apply_scale
            )
        except Exception as e:
            logger.error(f"Drag-and-drop import_scene.max call failed: {e}\n{traceback.format_exc()}")
            self.report({'ERROR'}, f"Drag-and-drop 3ds Max import failed: {e}. See log.")
            return {'CANCELLED'}

class ImportMaxFileHandler(FileHandler):
    bl_idname = "IMPORT_SCENE_FH_max"
    bl_label = "3ds Max Importer File Handler"
    bl_import_operator = "invoke_import_scene.max"
    bl_file_extensions = ".max"
    @classmethod
    def poll_drop(cls, context): return context.area.type in {'VIEW_3D', 'OUTLINER'}

def menu_func_export(self, context):
    self.layout.operator(ExportMax.bl_idname, text="Autodesk 3ds Max (.max)")

def menu_func_import(self, context):
    self.layout.operator(ImportMax.bl_idname, text="Autodesk 3ds Max (.max)")

def register():
    bpy.utils.register_class(PREFERENCES_OT_detect_max_python)
    bpy.utils.register_class(MaxPreferences)
    bpy.utils.register_class(ExportMax)
    bpy.utils.register_class(ImportMax)
    bpy.utils.register_class(InvokeExportMax)
    bpy.utils.register_class(InvokeImportMax)
    bpy.utils.register_class(ImportMaxFileHandler)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    logger.info("3ds Max Import/Export Addon registered successfully with new features.")

def unregister():
    bpy.utils.unregister_class(PREFERENCES_OT_detect_max_python)
    bpy.utils.unregister_class(MaxPreferences)
    bpy.utils.unregister_class(ExportMax)
    bpy.utils.unregister_class(ImportMax)
    bpy.utils.unregister_class(InvokeExportMax)
    bpy.utils.unregister_class(InvokeImportMax)
    bpy.utils.unregister_class(ImportMaxFileHandler)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    logger.info("3ds Max Import/Export Addon unregistered.")

if __name__ == "__main__":
    # This block is for direct script execution testing (unregister first, then register)
    # try: unregister() except Exception: pass
    # register()
    pass # Standard addons don't run register directly in __main__ typically