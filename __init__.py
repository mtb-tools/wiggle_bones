bl_info = {
    "name": "Wiggle Bone",
    "author": "Steve Miller",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "Properties > Bone",
    "description": "Simulates simple jiggle physics on bones",
    "warning": "",
    "wiki_url": "",
    "category": "Animation",
}

import bpy, math, mathutils
from mathutils import Vector,Matrix
from bpy.app.handlers import persistent

def jiggle_list_refresh():
    #iterate through all objects and bones to construct jiggle lists
    bpy.context.scene.jiggle_list.clear()
    for ob in bpy.context.scene.objects:
        if ob.type == 'ARMATURE':
            ob.jiggle_list.clear()
            for b in ob.pose.bones:
                if b.jiggle_enable:
                    item=ob.jiggle_list.add()
                    item.name = b.name
                    b['jiggle_mat']=b.matrix.copy()
                    print("added %s" %b.name)
            if ob.jiggle_list:
                item=bpy.context.scene.jiggle_list.add()
                item.name = ob.name
    #print('list refreshed')
                
def jiggle_list_refresh_ui(self,context):
    jiggle_list_refresh()
                    
#return m2 vector in m1 space
def relative_vector(m1,m2):
    mat = m2.inverted() @ m1
    vec = (mat.inverted().to_euler().to_matrix().to_4x4() @ Matrix.Translation(mat.translation)).translation
    return vec

def jiggle_bone(b):
    #translational movement between frames in bone's orientation space
    vec = relative_vector(b.matrix, Matrix(b['jiggle_mat']))  

    #rotational movement between frames
    rot1 = b.id_data.convert_space(pose_bone = b, matrix=Matrix(b['jiggle_mat']),from_space='WORLD', to_space='LOCAL').to_euler()
    if b.rotation_mode == 'QUATERNION':
        rot2 = b.rotation_quaternion.to_euler()
    else:
        rot2 = b.rotation_euler
    deltarot = Vector((rot1.z-rot2.z, 0, rot2.x-rot1.x))
                        
    b['jiggle_mat']=b.matrix.copy()
    tension = Vector(b.jiggle_spring)+vec
    if b.jiggle_animated:
        #print(deltarot)
        tension += deltarot
    b.jiggle_velocity = (Vector(b.jiggle_velocity)-tension*b.jiggle_stiffness)*(1-b.jiggle_dampen)
    b.jiggle_spring = tension+Vector(b.jiggle_velocity)
    
    #first frame should not consider any previous frame
    if bpy.context.scene.frame_current == bpy.context.scene.frame_start:
        vec = Vector((0,0,0))
        deltarot = Vector((0,0,0))
        b.jiggle_velocity = Vector((0,0,0))
        b.jiggle_spring = Vector((0,0,0))
        tension = Vector((0,0,0))
    
    additional = Vector((0,0,0))
    if b.jiggle_animated:
        if b.rotation_mode=='QUATERNION':
            additional = b.rotation_quaternion.to_euler()
        else:
            additional = b.rotation_euler
    if b.rotation_mode == 'QUATERNION':
        rotation_euler = b.rotation_quaternion.to_euler()
    else:
        rotation_euler = b.rotation_euler
    if b.rotation_mode == 'QUATERNION':
        rotation_euler.x = additional.x + math.radians(tension.z*-b.jiggle_amplitude)
        rotation_euler.z = additional.z + math.radians(tension.x*+b.jiggle_amplitude)
    else:
        rotation_euler.x = additional.x + math.radians(tension.z*-b.jiggle_amplitude)
        rotation_euler.z = additional.z + math.radians(tension.x*+b.jiggle_amplitude)
        
    #if not (bpy.context.scene.frame_current == bpy.context.scene.frame_start):
    if b.rotation_mode == 'QUATERNION':
        b.rotation_quaternion = rotation_euler.to_quaternion()
    else:
        b.rotation_euler = rotation_euler
    b.scale.y = 1-vec.y*b.jiggle_stretch

@persistent
def jiggle_bone_noanim(self):
    for item in bpy.context.scene.jiggle_list:
        if bpy.data.objects.find(item.name) >= 0:
            ob = bpy.data.objects[item.name]
            if ob.type == 'ARMATURE':
                for item2 in ob.jiggle_list:
                    if ob.pose.bones.find(item2.name) >= 0:
                        b = ob.pose.bones[item2.name]
                        if b.jiggle_enable:
                            if not b.jiggle_animated:
                                #print('jiggling %s' %b.name)
                                jiggle_bone(b)

@persistent                
def jiggle_bone_anim(self):
    for item in bpy.context.scene.jiggle_list:
        if bpy.data.objects.find(item.name) >= 0:
            ob = bpy.data.objects[item.name]
            if ob.type == 'ARMATURE':
                for item2 in ob.jiggle_list:
                    if ob.pose.bones.find(item2.name) >= 0:
                        b = ob.pose.bones[item2.name]
                        if b.jiggle_enable:
                            if b.jiggle_animated:
                                jiggle_bone(b)
                            #regardless of animation, always grab copy of matrix on late update of first frame
                            if bpy.context.scene.frame_current == bpy.context.scene.frame_start:
                                b['jiggle_mat']=b.matrix.copy()
    
class JiggleBonePanel(bpy.types.Panel):
    bl_label = 'Wiggle Bone'
    bl_idname = 'OBJECT_PT_jiggle_panel'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'bone'
    
    def draw(self,context):
        layout = self.layout
        b = context.active_pose_bone
        layout.prop(b, 'jiggle_enable')
        layout.prop(b, 'jiggle_animated')
        layout.prop(b, 'jiggle_stiffness')
        layout.prop(b,'jiggle_dampen')
        layout.prop(b, 'jiggle_amplitude')
        layout.prop(b, 'jiggle_stretch')
        
class jiggle_bone_item(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()

def register():
    
    bpy.utils.register_class(jiggle_bone_item)
    bpy.utils.register_class(JiggleBonePanel)
    
    bpy.types.PoseBone.jiggle_spring = bpy.props.FloatVectorProperty(default=Vector((0,0,0)))
    bpy.types.PoseBone.jiggle_velocity = bpy.props.FloatVectorProperty(default=Vector((0,0,0)))
    bpy.types.Scene.jiggle_list = bpy.props.CollectionProperty(type=jiggle_bone_item)
    bpy.types.Object.jiggle_list = bpy.props.CollectionProperty(type=jiggle_bone_item)
    bpy.types.PoseBone.jiggle_enable = bpy.props.BoolProperty(
        name = 'Enabled:',
        description = 'activate as jiggle bone',
        default = False,
        update = jiggle_list_refresh_ui
    )
    bpy.types.PoseBone.jiggle_animated = bpy.props.BoolProperty(
        name = 'Animated:',
        description = 'enable if bone has rotational keyframes',
        default = False
    )
    bpy.types.PoseBone.jiggle_dampen = bpy.props.FloatProperty(
        name = 'Dampening:',
        description = '0-1 range of how much tension is lost per frame, higher values settle quicker',
        default = 0.2
    )
    bpy.types.PoseBone.jiggle_stiffness = bpy.props.FloatProperty(
        name = 'Stiffness:',
        description = '0-1 range of how quickly bone tries to get to neutral state, higher values give faster jiggle',
        default = 0.2
    )
    bpy.types.PoseBone.jiggle_amplitude = bpy.props.FloatProperty(
        name = 'Amplitude:',
        description = 'Multiplier for the amplitude of the spring, higher values make larger jiggles',
        default = 30
    )
    bpy.types.PoseBone.jiggle_stretch = bpy.props.FloatProperty(
        name = 'Stretching:',
        description = '0-1 range for how much the jiggle stretches the bone, higher values stretch more',
        default = .4
    )
    
    #bpy.app.handlers.frame_change_pre.clear()
    #bpy.app.handlers.frame_change_post.clear()
    bpy.app.handlers.frame_change_pre.append(jiggle_bone_noanim)
    bpy.app.handlers.frame_change_post.append(jiggle_bone_anim)

def unregister():
    bpy.utils.unregister_class(JiggleBonePanel)
    bpy.utils.unregister_class(jiggle_bone_item)
    
    bpy.app.handlers.frame_change_pre.remove(jiggle_bone_noanim)
    bpy.app.handlers.frame_change_post.remove(jiggle_bone_anim)

if __name__ == "__main__":
    register()

#TODO
#jiggle props into property group < seems to not work for defaut vals/descriptions/etc and : vs = assignment

#run as addon [DONE]
#rotational momentum on animated bones [kinda done]

#handle quaternion rotation? [DONE]

#gravity?
#simple collision?
#reset physics on start frame [DONE]
