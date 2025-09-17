<img width="1200" height="600" alt="image" src="https://github.com/user-attachments/assets/87e8eab3-3a7f-4620-b121-9a705ae82e40" /><img width="1200" height="600" alt="image" src="https://github.com/user-attachments/assets/2f37cb48-e297-4421-99c0-9d853d408049" />
****

AUTODESK 3DS MAX FILE IMPORT-EXPORT ADDON
DOCUMENTATION

==============================================================================
TABLE OF CONTENTS
==============================================================================

1. Overview
2. Installation
3. System Requirements
4. Configuration
5. Importing 3ds Max Files
6. Exporting to 3ds Max
7. Advanced Settings
8. Troubleshooting
9. FAQ
10. Support

==============================================================================
1. OVERVIEW
==============================================================================

The Autodesk 3ds Max File Import-Export addon provides seamless integration 
between Blender and Autodesk 3ds Max through native .max file support. The 
addon uses intelligent FBX intermediate conversion to maintain scene integrity, 
materials, animations, and object hierarchies during file transfer.

Key Features:
- Direct .max file import/export
- Selective asset filtering (models, lights, cameras, splines, animations)
- Automatic 3ds Max installation detection
- Drag-and-drop file support
- Comprehensive logging system
- Professional workflow integration

==============================================================================
2. INSTALLATION
==============================================================================

Standard Installation:
1. Download the addon zip file
2. Open Blender and go to Edit > Preferences > Add-ons
3. Click "Install..." and select the downloaded zip file
4. Enable the addon by checking the box next to "Autodesk 3ds Max File Import-Export"
5. Configure the 3ds Max Python path (see Configuration section)

Manual Installation:
1. Extract the addon to your Blender addons folder:
   - Windows: %APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\
2. Restart Blender
3. Enable the addon in Preferences > Add-ons

==============================================================================
3. SYSTEM REQUIREMENTS
==============================================================================

- Operating System: Windows 10/11 (64-bit)
- Blender: Version 3.0 or later
- Autodesk 3ds Max: Version 2020 or later (any edition)
- Python: Compatible with your 3ds Max installation
- Disk Space: 50MB minimum for temporary file operations
- RAM: 4GB minimum, 8GB recommended for large scenes

Important Notes:
- This addon requires a working Autodesk 3ds Max installation
- Linux and macOS are not currently supported
- Administrative privileges may be required for initial setup

==============================================================================
4. CONFIGURATION
==============================================================================

Initial Setup:
1. Go to Edit > Preferences > Add-ons
2. Find "Autodesk 3ds Max File Import-Export" and expand its settings
3. Click "Auto Detect" to automatically find your 3ds Max Python path
4. If auto-detection fails, manually browse to your 3ds Max Python executable:
   Example paths:
   - C:\Program Files\Autodesk\3ds Max 2025\Python\python.exe
   - C:\Program Files\Autodesk\3ds Max 2024\bin\python.exe

Default Import Settings:
Configure default behavior for imported assets:
- Models: Import mesh objects (default: enabled)
- Lights: Import light objects (default: enabled)
- Cameras: Import camera objects (default: enabled)
- Splines: Import curve/spline objects (default: enabled)
- Animations: Import animation data (default: enabled)
- Materials: Import and assign materials (default: enabled)
- Armatures: Import skeleton/bone structures (default: enabled)
- Apply X-Axis 180° Rotation: Coordinate system adjustment (default: disabled)
- Apply 0.01 Scale: Unit conversion scaling (default: enabled)

==============================================================================
5. IMPORTING 3DS MAX FILES
==============================================================================

Method 1: File Menu
1. Go to File > Import > Autodesk 3ds Max (.max)
2. Browse and select your .max file
3. Configure import options in the dialog
4. Click "Import"

Method 2: Drag and Drop
1. Simply drag a .max file from Windows Explorer into the Blender viewport
2. An options dialog will appear
3. Configure settings and click "OK"

Import Options:
- Models: Include mesh geometry
- Lights: Include lighting setup
- Cameras: Include camera objects and settings
- Splines: Include curves and NURBS
- Animations: Include keyframe and procedural animations
- Materials: Include material assignments and properties
- Armatures: Include bone systems and rigging
- Apply X-Axis 180° Rotation: Correct coordinate system differences
- Apply 0.01 Scale: Convert from 3ds Max units to Blender units

Tips for Successful Import:
- Larger files may take several minutes to process
- Check the system console for progress updates
- Ensure sufficient disk space for temporary files
- Close other intensive applications during import

==============================================================================
6. EXPORTING TO 3DS MAX
==============================================================================

Standard Export:
1. Go to File > Export > Autodesk 3ds Max (.max)
2. Choose destination and filename
3. Configure export options
4. Click "Export"

Export Options:
- Models: Export mesh objects
- Lights: Export lighting setup
- Cameras: Export camera objects
- Splines: Export curves and paths
- Animations: Export animation data
- Selection Only: Export only selected objects

Export Process:
1. Blender creates an intermediate FBX file
2. 3ds Max loads the FBX and converts to .max format
3. Temporary files are automatically cleaned up
4. Final .max file is saved to your specified location

Best Practices:
- Apply transforms before export for better compatibility
- Use standard materials for maximum compatibility
- Test exports with simple scenes first
- Verify 3ds Max can open exported files

==============================================================================
7. ADVANCED SETTINGS
==============================================================================

Logging System:
- Detailed logs are saved to: Documents\blender_3dsmax_log.txt
- Logs include conversion steps, errors, and performance metrics
- Review logs for troubleshooting failed operations

Cache Directory:
- Temporary files stored in: Documents\blender_3dsmax_cache\
- Automatically cleaned after operations
- Can be manually cleared if needed

Performance Optimization:
- Close unnecessary applications during conversion
- Use SSD storage for faster file operations
- Increase virtual memory for large scene handling
- Monitor system resources during operations

==============================================================================
8. TROUBLESHOOTING
==============================================================================

Common Issues and Solutions:

"3ds Max Python executable not found"
- Solution: Verify 3ds Max is installed and use Auto Detect
- Alternative: Manually set the Python path in preferences

"FBX export failed"
- Solution: Check selected objects are valid mesh/curve data
- Ensure scene doesn't contain unsupported object types
- Try exporting individual objects to isolate issues

"3ds Max script execution failed"
- Solution: Verify 3ds Max installation is not corrupted
- Check available disk space and memory
- Try restarting Blender and 3ds Max

"Import results in empty scene"
- Solution: Check import filters - ensure desired assets are enabled
- Verify source .max file is not corrupted
- Check log file for specific error messages

Conversion takes too long:
- Reduce scene complexity before conversion
- Close other applications to free system resources
- Consider breaking large scenes into smaller parts

File size issues:
- Large textures may slow conversion - optimize beforehand
- High polygon count models require more processing time
- Complex animation data increases conversion duration

==============================================================================
9. FAQ
==============================================================================

Q: What versions of 3ds Max are supported?
A: 3ds Max 2020 and later. The addon automatically detects the highest 
   installed version.

Q: Can I use this without 3ds Max installed?
A: No, a working 3ds Max installation is required for file conversion.

Q: Are materials preserved during conversion?
A: Yes, when import materials is enabled. Material fidelity depends on 
   compatibility between 3ds Max and Blender material systems.

Q: What happens to animations during import/export?
A: Keyframe animations are preserved. Complex procedural animations may 
   require manual adjustment.

Q: Can I batch convert multiple files?
A: Currently, files must be converted individually. Batch processing may 
   be added in future versions.

Q: Why use FBX as intermediate format?
A: FBX provides the best compatibility for transferring complex 3D data 
   between 3ds Max and Blender while preserving most scene elements.

Q: Is this addon compatible with Blender's extensions system?
A: Yes, the addon includes a proper manifest file for Blender 4.2+ 
   extensions system.

==============================================================================
10. SUPPORT
==============================================================================

Getting Help:
1. Check this documentation first
2. Review the log file at Documents\blender_3dsmax_log.txt
3. Search common issues in the troubleshooting section
4. Contact support with specific error messages and log files

Reporting Issues:
When reporting problems, please include:
- Blender version
- 3ds Max version
- Operating system details
- Complete error messages
- Steps to reproduce the issue
- Log file contents (if applicable)

Performance Tips:
- Keep 3ds Max and Blender updated to latest versions
- Maintain adequate free disk space (minimum 10GB recommended)
- Close unnecessary applications during file conversion
- Use wired network connection for better stability if accessing network files

Updates and Changelog:
Check the addon description for update notifications and version history.
Major updates may include new features, bug fixes, and compatibility improvements.

==============================================================================

Thank you for using the Autodesk 3ds Max File Import-Export addon!
This documentation covers the core functionality and common use cases.
For advanced workflows or specific technical requirements, please refer
to the troubleshooting section or contact support.

Version: 1.0.0
Last Updated: 2024
