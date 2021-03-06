from os.path import join
import stat
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import call, Mock, patch

from rerun.rerun import (
    get_changed_files, clear_screen, get_file_mtime, has_file_changed,
    is_ignorable, main, mainloop, skip_dirs, SKIP_DIRS, SKIP_EXT, step
)


class Test_Rerun(unittest.TestCase):

    @patch('rerun.rerun.os')
    def test_get_file_stats(self, mock_os):
        def mock_stat(filename):
            self.assertEqual(filename, 'hello')
            return mock_filestat
        mock_os.stat = mock_stat
        mock_filestat = {stat.ST_MTIME: 'mymtime'}

        time = get_file_mtime('hello')

        self.assertEqual(time, 'mymtime')


    def test_skip_dirs_modifies_in_place(self):
        dirs = ['a', 'b', 'c', 'd', 'e', 'f'] 
        skip_dirs(dirs, ['b', 'd', 'f'])
        self.assertEqual(dirs, ['a', 'c', 'e'])


    def test_is_ignorable(self):
        self.assertFalse(is_ignorable('h.txt', []))


    def test_is_ignorable_for_ignored(self):
        self.assertTrue(is_ignorable('h.txt', ['h.txt']))


    def test_is_ignorable_for_ignored_with_same_ending(self):
        self.assertFalse(is_ignorable('gh.txt', ['h.txt']))


    def test_is_ignorable_works_on_basename(self):
        self.assertTrue(is_ignorable(r'somedir/h.txt', ['h.txt']))


    def test_is_ignorable_for_extension(self):
        self.assertTrue(is_ignorable('h' + SKIP_EXT[0], []))


    @patch('rerun.rerun.get_file_mtime')
    def test_has_file_changed_return_value(self, mock_get_file_stats):
        file_stats = ['mon', 'mon', 'tue', 'tue']
        mock_get_file_stats.side_effect = lambda _: file_stats.pop(0)

        self.assertTrue(has_file_changed('filename'))
        self.assertFalse(has_file_changed('filename'))
        self.assertTrue(has_file_changed('filename'))
        self.assertFalse(has_file_changed('filename'))


    @patch('rerun.rerun.has_file_changed')
    @patch('rerun.rerun.os')
    def test_get_changed_files(self, mock_os, mock_changed):
        mock_os.walk.return_value = [
            ('root1', list('dirs1'), list('files')),
        ]
        mock_os.path.join = join
        # one bool for each file in ['f' 'i' 'l' 'e' 's']
        has_file_changed_values = [
            True, False, False, False, True,   # 1st & last file changed
        ]
        mock_changed.side_effect = lambda _: has_file_changed_values.pop(0)

        actual = get_changed_files([])

        self.assertEqual(actual, [join('root1', 'f'), join('root1', 's')])
        # must call has_file_changed for every file, cannot short-circuit
        self.assertEqual(mock_changed.call_count, 5)


    @patch('rerun.rerun.os')
    @patch('rerun.rerun.skip_dirs')
    def test_get_changed_files_calls_skip_dirs(self, mock_skip_dirs, mock_os):
        mock_os.walk.return_value = [
            ('root1', list('dirs1'), list('files')),
            ('root2', list('dirs2'), list('files')),
        ]
        ignoreds = []

        get_changed_files(ignoreds)

        self.assertEqual(
            mock_skip_dirs.call_args_list,
            [
                ((list('dirs1'), ignoreds), ),
                ((list('dirs2'), ignoreds), ),
            ]
        )


    @patch('rerun.rerun.platform')
    @patch('rerun.rerun.os.system')
    def test_clear_screen(self, mock_system, mock_platform):
        mock_platform.system.return_value = 'Windows'
        clear_screen()
        self.assertEqual(mock_system.call_args[0], ('cls',))

        mock_platform.system.return_value = 'win32'
        clear_screen()
        self.assertEqual(mock_system.call_args[0], ('cls',))

        mock_platform.system.return_value = 'win64'
        clear_screen()
        self.assertEqual(mock_system.call_args[0], ('cls',))

        mock_platform.system.return_value = 'Darwin'
        clear_screen()
        self.assertEqual(mock_system.call_args[0], ('clear',))

        mock_platform.system.return_value = 'unknown'
        clear_screen()
        self.assertEqual(mock_system.call_args[0], ('clear',))


    @patch('rerun.rerun.get_changed_files')
    @patch('rerun.rerun.clear_screen')
    @patch('rerun.rerun.subprocess')
    @patch('rerun.rerun.time.sleep', Mock())
    def test_step_no_changes(
        self, mock_subprocess, mock_clear_screen, mock_get_changed_files,
    ):
        mock_get_changed_files.return_value = []

        step(True, Mock())

        self.assertFalse(mock_clear_screen.called)
        self.assertFalse(mock_subprocess.call.called)


    @patch('sys.stdout')
    @patch('rerun.rerun.get_changed_files')
    @patch('rerun.rerun.is_ignorable')
    @patch('rerun.rerun.clear_screen')
    @patch('rerun.rerun.subprocess')
    @patch('rerun.rerun.time.sleep', Mock())
    def test_step_with_changes(
        self, mock_subprocess, mock_clear_screen, mock_is_ignorable,
        mock_get_changed_files, mock_stdout
    ):
        mock_get_changed_files.return_value = ['myfile']
        mock_is_ignorable.return_value = False
        options = Mock(verbose=False)

        step(False, options)

        self.assertTrue(mock_clear_screen.called)
        self.assertTrue(mock_subprocess.call.called)
        self.assertFalse(mock_stdout.write.called)


    @patch('sys.stdout')
    @patch('rerun.rerun.get_changed_files')
    @patch('rerun.rerun.is_ignorable')
    @patch('rerun.rerun.clear_screen')
    @patch('rerun.rerun.subprocess')
    @patch('rerun.rerun.time.sleep', Mock())
    def test_step_with_changes_and_verbose_output(
        self, mock_subprocess, mock_clear_screen, mock_is_ignorable,
        mock_get_changed_files, mock_stdout
    ):
        mock_get_changed_files.return_value = ['myfile']
        mock_is_ignorable.return_value = False
        options = Mock(command='mycommand', verbose=True)

        step(False, options)

        self.assertTrue(mock_clear_screen.called)
        self.assertTrue(mock_subprocess.call.called)
        self.assertEqual(
            mock_stdout.write.call_args_list,
            [
                call('mycommand'), call('\n'),
                call('myfile'), call('\n'),
            ]
        )


    @patch('rerun.rerun.get_changed_files')
    @patch('rerun.rerun.is_ignorable')
    @patch('rerun.rerun.clear_screen')
    @patch('rerun.rerun.subprocess')
    @patch('rerun.rerun.time.sleep', Mock())
    def test_step_with_ignorable_changes(
        self, mock_subprocess, mock_clear_screen, mock_is_ignorable,
        mock_get_changed_files,
    ):
        mock_get_changed_files.return_value = ['myfile']
        mock_is_ignorable.return_value = True

        step(False, Mock())

        self.assertFalse(mock_clear_screen.called)
        self.assertFalse(mock_subprocess.call.called)


    @patch('rerun.rerun.step')
    def test_mainloop(self, mock_step):
        calls = []

        def raise_after_3(first_time, options):
            calls.append(0)
            if len(calls) == 3:
                raise ZeroDivisionError()

        mock_step.side_effect = raise_after_3

        options = Mock()
        with self.assertRaises(ZeroDivisionError):
            mainloop(options)

        self.assertEqual(
            mock_step.call_args_list,
            [
                call(True, options),
                call(False, options),
                call(False, options),
            ]
        )


    @patch('rerun.rerun.sys.argv', [1, 2, 3])
    @patch('rerun.rerun.get_parser')
    @patch('rerun.rerun.parse_args')
    @patch('rerun.rerun.validate')
    @patch('rerun.rerun.mainloop')
    def test_main(
        self, mock_mainloop, mock_validate, mock_parse_args, mock_get_parser
    ):

        main()

        self.assertEqual(
            mock_get_parser.call_args,
            (('rerun', SKIP_DIRS, SKIP_EXT), )
        )
        self.assertEqual(
            mock_parse_args.call_args,
            ((mock_get_parser.return_value, [2, 3]),)
        )
        self.assertEqual(
            mock_validate.call_args,
            ((mock_parse_args.return_value, ),)
        )
        self.assertEqual(
            mock_mainloop.call_args,
            ((mock_validate.return_value, ),)
        )

