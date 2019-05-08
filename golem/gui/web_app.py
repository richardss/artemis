"""Golem GUI main web app blueprint"""
import os

from flask import abort, redirect, render_template, request, url_for
from flask.blueprints import Blueprint
from flask_login import current_user, login_user, login_required, logout_user

from golem.core import (environment_manager, page_object, settings_manager, test_case,
                        session, utils)
from golem.core import test_data as test_data_module
from golem.core import suite as suite_module

from . import gui_utils, user
from .gui_utils import project_exists, gui_permissions_required


webapp_bp = Blueprint('webapp', __name__)


# LOGIN VIEW
@webapp_bp.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('webapp.index'))
    if request.method == 'POST':
        errors = []
        user_data = {}
        username = request.form['username']
        password = request.form['password']
        next_url = request.form['next']
        if not username:
            errors.append('Username is required')
        elif not password:
            errors.append('Password is required')
        else:
            user_data = user.get_user_data(username=username)
            if user_data is None:
                errors.append('Username does not exists')
            elif user_data['password'] != password:
                errors.append('Username and password do not match')
        if len(errors):
            return render_template('login.html', next_url=next_url, errors=errors)
        else:
            usr = user.User(user_data['id'], user_data['username'],
                            user_data['is_admin'], user_data['gui_projects'],
                            user_data['report_projects'])
            login_user(usr)
            if not next_url or not gui_utils.is_safe_url(next_url):
                next_url = '/'
            return redirect(next_url)
    else:
        next_url = request.args.get('next')
        if not next_url or not gui_utils.is_safe_url(next_url):
            next_url = '/'
        return render_template('login.html', next_url=next_url, errors=[])


# INDEX VIEW
@webapp_bp.route("/")
@login_required
def index():
    """If user is admin or has '*' in report permissions they will
    have access to every project. Otherwise limit the project
    list to gui_permissions
    """
    if current_user.is_admin or '*' in current_user.gui_permissions:
        projects = utils.get_projects()
    else:
        projects = current_user.gui_permissions
    return render_template('index.html', projects=projects)


# PROJECT VIEW - redirect to to /project/suites/
@webapp_bp.route("/project/<project>/")
@login_required
@project_exists
@gui_permissions_required
def project_view(project):
    return redirect('/project/{}/suites/'.format(project))


# PROJECT TESTS VIEW
@webapp_bp.route("/project/<project>/tests/")
@login_required
@project_exists
@gui_permissions_required
def project_tests(project):
    return render_template('list/test_list.html', project=project)


# PROJECT SUITES VIEW
@webapp_bp.route("/project/<project>/suites/")
@login_required
@project_exists
@gui_permissions_required
def project_suites(project):
    return render_template('list/suite_list.html', project=project)


# PROJECT PAGES VIEW
@webapp_bp.route("/project/<project>/pages/")
@login_required
@project_exists
@gui_permissions_required
def project_pages(project):
    return render_template('list/page_list.html', project=project)


# TEST CASE VIEW
@webapp_bp.route("/project/<project>/test/<test_case_name>/")
@login_required
@project_exists
@gui_permissions_required
def test_case_view(project, test_case_name):
    test_exists = test_case.test_case_exists(project, test_case_name)
    if not test_exists:
        abort(404, 'The test {} does not exist'.format(test_case_name))
    tc_name, parents = utils.separate_file_from_parents(test_case_name)
    path = test_case.test_file_path(project, test_case_name)
    _, error = utils.import_module(path)
    if error:
        url = url_for('webapp.test_case_code_view', project=project,
                      test_case_name=test_case_name)
        content = ('<h4>There are errors in the test</h4>'
                   '<p>There are errors and the test cannot be displayed, '
                   'open the test code editor to solve them.</p>'
                   '<a class="btn btn-default" href="{}">Open Test Code</a>'
                   .format(url))
        return render_template('common_element_error.html', project=project,
                               item_name=test_case_name, content=content)
    else:
        test_case_contents = test_case.get_test_case_content(project, test_case_name)
        test_data = test_data_module.get_test_data(project, test_case_name,
                                                   repr_strings=True)
        return render_template('test_builder/test_case.html', project=project,
                               test_case_contents=test_case_contents,
                               test_case_name=tc_name,
                               full_test_case_name=test_case_name,
                               test_data=test_data)


# TEST CASE CODE VIEW
@webapp_bp.route("/project/<project>/test/<test_case_name>/code/")
@login_required
@project_exists
@gui_permissions_required
def test_case_code_view(project, test_case_name):
    test_exists = test_case.test_case_exists(project, test_case_name)
    if not test_exists:
        abort(404, 'The test {} does not exist'.format(test_case_name))
    tc_name, parents = utils.separate_file_from_parents(test_case_name)
    path = os.path.join(session.testdir, 'projects', project,
                        'tests', os.sep.join(parents), tc_name + '.py')
    test_case_contents = test_case.get_test_case_code(path)
    _, error = utils.import_module(path)
    external_data = test_data_module.get_external_test_data(project, test_case_name)
    test_data_setting = session.settings['test_data']
    return render_template('test_builder/test_case_code.html', project=project,
                           test_case_contents=test_case_contents, test_case_name=tc_name,
                           full_test_case_name=test_case_name, test_data=external_data,
                           test_data_setting=test_data_setting, error=error)


# PAGE OBJECT VIEW
@webapp_bp.route("/project/<project>/page/<full_page_name>/")
@login_required
@project_exists
@gui_permissions_required
def page_view(project, full_page_name, no_sidebar=False):
    path = page_object.page_file_path(project, full_page_name)
    page_exists_ = page_object.page_exists(project, full_page_name)
    if not page_exists_:
        abort(404, 'The page {} does not exist'.format(full_page_name))
    _, error = utils.import_module(path)
    if error:
        if no_sidebar:
            url = url_for('webapp.page_code_view_no_sidebar', project=project,
                          full_page_name=full_page_name)
        else:
            url = url_for('webapp.page_code_view', project=project,
                          full_page_name=full_page_name)
        content = ('<h4>There are errors in the page</h4>'
                   '<p>There are errors and the page cannot be displayed, '
                   'open the page code editor to solve them.</p>'
                   '<a class="btn btn-default" href="{}">Open Page Code</a>'
                   .format(url))
        return render_template('common_element_error.html', project=project,
                               item_name=full_page_name, content=content,
                               no_sidebar=no_sidebar)
    else:
        page_data = page_object.get_page_object_content(project, full_page_name)
        return render_template('page_builder/page_object.html',
                               project=project,
                               page_object_data=page_data,
                               page_name=full_page_name,
                               no_sidebar=no_sidebar)


# PAGE OBJECT VIEW no sidebar
@webapp_bp.route("/project/<project>/page/<full_page_name>/no_sidebar/")
@login_required
def page_view_no_sidebar(project, full_page_name):
    return page_view(project=project, full_page_name=full_page_name, no_sidebar=True)


# PAGE OBJECT CODE VIEW
@webapp_bp.route("/project/<project>/page/<full_page_name>/code/")
@login_required
@project_exists
@gui_permissions_required
def page_code_view(project, full_page_name, no_sidebar=False):
    page_exists_ = page_object.page_exists(project, full_page_name)
    if not page_exists_:
        abort(404, 'The page {} does not exist'.format(full_page_name))
    path = page_object.page_file_path(project, full_page_name)
    _, error = utils.import_module(path)
    page_object_code = page_object.get_page_object_code(path)
    return render_template('page_builder/page_object_code.html', project=project,
                           page_object_code=page_object_code, page_name=full_page_name,
                           error=error, no_sidebar=no_sidebar)


# PAGE OBJECT CODE VIEW no sidebar
@webapp_bp.route("/project/<project>/page/<full_page_name>/no_sidebar/code/")
@login_required
def page_code_view_no_sidebar(project, full_page_name):
    return page_code_view(project=project, full_page_name=full_page_name, no_sidebar=True)


# SUITE VIEW
@webapp_bp.route("/project/<project>/suite/<suite>/")
@login_required
@project_exists
@gui_permissions_required
def suite_view(project, suite):
    if not suite_module.suite_exists(project, suite):
        abort(404, 'The suite {} does not exist'.format(suite))
    all_test_cases = utils.get_test_cases(project)
    selected_tests = suite_module.get_suite_test_cases(project, suite)
    processes = suite_module.get_suite_amount_of_processes(project, suite)
    browsers = suite_module.get_suite_browsers(project, suite)
    default_browser = session.settings['default_browser']
    environments = suite_module.get_suite_environments(project, suite)
    tags = suite_module.get_tags(project, suite)
    return render_template('suite.html', project=project,
                           all_test_cases=all_test_cases['sub_elements'],
                           selected_tests=selected_tests, suite=suite,
                           processes=processes, browsers=browsers,
                           default_browser=default_browser, environments=environments,
                           tags=tags)


# GLOBAL SETTINGS VIEW
@webapp_bp.route("/settings/")
@login_required
def global_settings():
    settings = settings_manager.get_global_settings_as_string()
    return render_template('settings.html', project=None, global_settings=settings,
                           settings=None)


# PROJECT SETTINGS VIEW
@webapp_bp.route("/project/<project>/settings/")
@login_required
@project_exists
@gui_permissions_required
def project_settings(project):
    gsettings = settings_manager.get_global_settings_as_string()
    psettings = settings_manager.get_project_settings_as_string(project)
    return render_template('settings.html', project=project, global_settings=gsettings,
                           settings=psettings)


# ENVIRONMENTS VIEW
@webapp_bp.route("/project/<project>/environments/")
@login_required
@project_exists
@gui_permissions_required
def environments_view(project):
    data = environment_manager.get_environments_as_string(project)
    return render_template('environments.html', project=project, environment_data=data)


# LOGOUT VIEW
@webapp_bp.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect('/')