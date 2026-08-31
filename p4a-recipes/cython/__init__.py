from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class CythonRecipe(CompiledComponentsPythonRecipe):
    """覆盖 p4a 内置的 cython recipe。

    背景：p4a master 的 python3 recipe 默认构建 **Python 3.14.2**，
    但其内置 cython recipe 仍是 **0.29.36**。Cython 0.29.x 不支持
    Python 3.13/3.14（Py_UNICODE 自 3.13 起废弃、_PyLong_AsByteArray 在
    3.13 新增 with_exceptions 参数导致签名不符），cython 的 C 扩展
    编译必然失败（clang 报 2 errors generated）。

    本 recipe 把版本提升到 **3.1.8**，它是 Cython 3.1 系列专门为支持
    Python 3.13/3.14 而发布的版本，且仍提供 setup.py（p4a 的
    CompiledComponentsPythonRecipe 走 `setup.py build_ext` 路径）。

    兼容性已核验：
    - pygame-ce 2.5.0 的 build-system.requires 里 cython 无版本约束，
      且其 setup.py 用 `from Cython.Build.Dependencies import cythonize_one`，
      该 API 在 Cython 3.x 中存在。
    - p4a 的 local_recipes 优先于内置 recipes 搜索，同名会覆盖（已核验
      recipe.py 的 get_recipe 逻辑：local_recipes 命中即 break）。
    """

    version = '3.1.8'
    url = 'https://github.com/cython/cython/archive/refs/tags/{version}.tar.gz'
    site_packages_name = 'cython'
    name = 'cython'
    depends = ['setuptools']
    call_hostpython_via_targetpython = False
    install_in_hostpython = True


recipe = CythonRecipe()
