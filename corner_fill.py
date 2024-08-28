# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/1d_corner_fill

from bpy.types import Operator, Panel
from bpy.utils import register_class, unregister_class

bl_info = {
    "name": "Corner Fill",
    "description": "Fill closed vertices loop with polygons loop starting from selected vertices",
    "author": "Nikita Akimov, Paul Kotelevets",
    "version": (1, 0, 0),
    "blender": (2, 79, 0),
    "location": "View3D > Tool panel > 1D > OBJ Tools",
    "doc_url": "https://github.com/Korchy/1d_corner_fill",
    "tracker_url": "https://github.com/Korchy/1d_corner_fill",
    "category": "All"
}


# MAIN CLASS

class CornerFill:

    @classmethod
    def fill(cls, context, obj):
        # fills closed vertices loop with polygons loops starting from selected vertices
        print(obj)

    @staticmethod
    def ui(layout, context):
        # ui panel
        layout.operator(
            operator='corner_fill.fill',
            icon='SURFACE_NCIRCLE'
        )


# OPERATORS

class CornerFill_OT_fill(Operator):
    bl_idname = 'corner_fill.fill'
    bl_label = 'Corner Fill'
    bl_description = 'Fill from corners'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        CornerFill.fill(
            context=context,
            obj=context.object
        )
        return {'FINISHED'}


# PANELS

class CornerFill_PT_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = "Corner Fill"
    bl_category = '1D'

    def draw(self, context):
        CornerFill.ui(
            layout=self.layout,
            context=context
        )


# REGISTER

def register(ui=True):
    register_class(CornerFill_OT_fill)
    if ui:
        register_class(CornerFill_PT_panel)


def unregister(ui=True):
    if ui:
        unregister_class(CornerFill_PT_panel)
    unregister_class(CornerFill_OT_fill)


if __name__ == "__main__":
    register()
