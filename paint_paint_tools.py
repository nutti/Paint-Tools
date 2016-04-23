import numpy as np
import bpy
import bgl
from bpy.props import FloatVectorProperty

bl_info = {
    "name": "Paint Tools",
    "author": "Nutti",
    "version": (1, 0),
    "blender": (2, 77, 0),
    "location": "Image Editor > Paint Tools",
    "description": "Paint Tools for Blender",
    "warning": "",
    "support": "COMMUNITY",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Paint"
}


def runnable(context):
    is_edit_mode = (context.mode == 'EDIT_MESH')
    area, region, space = get_space('IMAGE_EDITOR', 'WINDOW', 'IMAGE_EDITOR', context)
    is_paint_mode = (space.mode == 'PAINT')

    return is_edit_mode and not is_paint_mode


def redraw_all_areas():
    for area in bpy.context.screen.areas:
        area.tag_redraw()


def get_space(area_type, region_type, space_type, context):
    for area in context.screen.areas:
        if area.type == area_type:
            break
    for region in area.regions:
        if region.type == region_type:
            break
    for space in area.spaces:
        if space.type == space_type:
            break

    return (area, region, space)


def get_active_image():
    area, region, space = get_space('IMAGE_EDITOR', 'WINDOW', 'IMAGE_EDITOR', bpy.context)
    return area.spaces.active.image


def to_pixel(context, mvx, mvy):
    mrx, mry = context.region.view2d.region_to_view(mvx, mvy)
    img = get_active_image()
    mpx = img.size[0] * mrx
    mpy = img.size[1] * mry
    return (mpx, mpy)


class FillRect(bpy.types.Operator):

    bl_idname = "uv.fill_rect"
    bl_label = "Fill Rect"
    bl_description = "Fill Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __fill_rect(self, data, w, h, x0, y0, x1, y1, color):
        ys = min(y0, y1) + 1
        ye = max(y0, y1) + 1
        xs = min(x0, x1)
        xe = max(x0, x1)
        for y in range(ye - ys):
            for x in range(xe - xs):
                offset = ((y + ys) * w + (x + xs)) * 4
                data[offset] = color[0]
                data[offset + 1] = color[1]
                data[offset + 2] = color[2]
                data[offset + 3] = 1.0

    def execute(self, context):
        scene = context.scene
        props = scene.pt_props
        img = get_active_image()
        pixels = np.array(img.pixels[:])
        num_pixels = int(len(pixels) / 4)
        width = img.size[0]
        height = img.size[0]
        x0, y0 = to_pixel(context, props.start[0], props.start[1])
        x1, y1 = to_pixel(context, props.end[0], props.end[1])

        self.__fill_rect(pixels, width, height, int(x0), int(y0), int(x1), int(y1), scene.pt_fill_color)

        img.pixels[:] = pixels.tolist()
        img.update()

        return {'FINISHED'}


class EraseRect(bpy.types.Operator):

    bl_idname = "uv.erase_rect"
    bl_label = "Erase Rect"
    bl_description = "Erase Rect"
    bl_options = {'REGISTER', 'UNDO'}

    def __fill_rect(self, data, w, h, x0, y0, x1, y1, color):
        ys = min(y0, y1) + 1
        ye = max(y0, y1) + 1
        xs = min(x0, x1)
        xe = max(x0, x1)
        for y in range(ye - ys):
            for x in range(xe - xs):
                offset = ((y + ys) * w + (x + xs)) * 4
                data[offset] = color[0]
                data[offset + 1] = color[1]
                data[offset + 2] = color[2]
                data[offset + 3] = 0.0

    def execute(self, context):
        scene = context.scene
        props = scene.pt_props
        img = get_active_image()
        pixels = np.array(img.pixels[:])
        num_pixels = int(len(pixels) / 4)
        width = img.size[0]
        height = img.size[0]
        x0, y0 = to_pixel(context, props.start[0], props.start[1])
        x1, y1 = to_pixel(context, props.end[0], props.end[1])

        self.__fill_rect(pixels, width, height, int(x0), int(y0), int(x1), int(y1), (0, 0, 0, 0))

        img.pixels[:] = pixels.tolist()
        img.update()

        return {'FINISHED'}


class BoxRenderer(bpy.types.Operator):

    bl_idname = "uv.box_renderer"
    bl_label = "Box Renderer"
    bl_description = "Bounding Box Renderer in Image Editor"

    __handle = None

    @staticmethod
    def handle_add(self, context):
        if BoxRenderer.__handle is None:
            BoxRenderer.__handle = bpy.types.SpaceImageEditor.draw_handler_add(
                BoxRenderer.draw_bb,
                (self, context), "WINDOW", "POST_PIXEL")

    @staticmethod
    def handle_remove(self, context):
        if BoxRenderer.__handle is not None:
            bpy.types.SpaceImageEditor.draw_handler_remove(
                BoxRenderer.__handle, "WINDOW")
            BoxRenderer.__handle = None

    @staticmethod
    def draw_bb(self, context):
        props = context.scene.pt_props
        x0, y0 = props.start
        x1, y1 = props.end

        verts = [
            [x0, y0],
            [x0, y1],
            [x1, y1],
            [x1, y0]
        ]

        bgl.glLineWidth(1)
        bgl.glBegin(bgl.GL_LINE_LOOP)
        bgl.glColor4f(1.0, 1.0, 1.0, 1.0)
        for (x, y) in verts:
            bgl.glVertex2f(x, y)
        bgl.glEnd()

    def modal(self, context, event):
        props = context.scene.pt_props
        redraw_all_areas()
        if props.running is False or not runnable(context):
            props.start = (event.mouse_region_x, event.mouse_region_y)
            props.end = props.start
            BoxRenderer.handle_remove(self, context)
            props.running = False
            return {'FINISHED'}

        if event.type == 'LEFTMOUSE':
            if not props.selecting and event.value == 'PRESS':
                area, region, space = get_space('IMAGE_EDITOR', 'WINDOW', 'IMAGE_EDITOR', context)
                out = False
                if region.width < event.mouse_region_x:
                    out = True
                if event.mouse_region_x < 0:
                    out = True
                if region.height < event.mouse_region_y:
                    out = True
                if region.height < 0:
                    out = True
                if not out:
                    props.selecting = True
                    props.start = (event.mouse_region_x, event.mouse_region_y)
                    props.end = props.start
            elif props.selecting and event.value == 'RELEASE':
                props.selecting = False
                props.end = (event.mouse_region_x, event.mouse_region_y)
        if event.type == 'MOUSEMOVE':
            if props.selecting:
                props.end = (event.mouse_region_x, event.mouse_region_y)

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        props = context.scene.pt_props
        if props.running is False:
            BoxRenderer.handle_add(self, context)
            context.window_manager.modal_handler_add(self)
            props.running = True
            props.selecting = False
            return {'RUNNING_MODAL'}
        else:
            props.running = False
        return {'FINISHED'}


class IMAGE_PT_PT(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_label = 'Painting Tool'

    @classmethod
    def poll(cls, context):
        return runnable(context)

    def draw(self, context):
        sc = context.scene
        props = sc.pt_props
        layout = self.layout
        layout.label(text="", icon='PLUGIN')
        layout.label(text="Rectangular Selection")
        if props.running == False:
            layout.operator(BoxRenderer.bl_idname, text="", icon='PLAY')
        else:
            layout.operator(BoxRenderer.bl_idname, text="", icon='PAUSE')
            split = layout.split()
            col = split.column()
            col.operator(FillRect.bl_idname, text="Fill")
            col.operator(EraseRect.bl_idname, text="Erase")
            col = split.column()
            col.prop(sc, "pt_fill_color", text="")

class PTProps():
    running = False
    selecting = False
    start = (0.0, 0.0)
    end = (0.0, 0.0)

def init_props():
    scene = bpy.types.Scene
    scene.pt_props = PTProps()
    scene.pt_fill_color = FloatVectorProperty(
        name="Fill Color",
        description="Filled by this color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),
        min=0.0,
        max=1.0)

def clear_props():
    scene = bpy.types.Scene
    del scene.pt_fill_color
    del scene.pt_props

def register():
    bpy.utils.register_module(__name__)
    init_props()

def unregister():
    bpy.utils.unregister_module(__name__)
    clear_props()

if __name__ == "__main__":
    register()
