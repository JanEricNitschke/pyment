"""Integration tests of pyment app."""

import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

import pyment.pyment


class AppTests(unittest.TestCase):
    """
    Test pyment as an app in a shell.

    It's an integration test.
    """

    # You have to run this as a module when testing so the relative imports work.
    CMD_PREFIX = sys.executable + " -m pyment.pymentapp {}"

    RE_TYPE = type(re.compile("get the type to test if an argument is an re"))

    # cwd to use when running subprocess.
    # It has to be at the repo directory so python -m can be used
    CWD = os.path.dirname(os.path.dirname(__file__))

    INPUT = textwrap.dedent('''

        def func():
            """First line

            :returns: smthg

            :rtype: ret type

            """
            pass
    ''')

    # Expected output in overwrite mode.
    EXPECTED_OUTPUT = textwrap.dedent('''\
        """_summary_."""

        def func():
            """First line.

            Returns
            -------
            ret type
                smthg
            """
            pass
    ''')

    PATCH_PREFIX = f"# Patch generated by Pyment v{pyment.pyment.__version__}"

    # a/- and b/- is replaced by a filename when not testing stdin/stdout
    EXPECTED_PATCH = textwrap.dedent(f'''\
        {PATCH_PREFIX}

        --- a/-
        +++ b/-
        @@ -1,11 +1,12 @@
        +"""_summary_."""

         def func():
        -    """First line
        +    """First line.

        -    :returns: smthg
        -
        -    :rtype: ret type
        -
        +    Returns
        +    -------
        +    ret type
        +        smthg
             """
             pass

    ''')

    # The format which will turn INPUT into EXPECTED_PATCH and EXPECTED_OUTPUT
    OUTPUT_FORMAT = "numpydoc"

    @classmethod
    def normalise_empty_lines(cls, lines):
        """
            Replace any lines that are only whitespace with a single \n

            textwrap.dedent removes all whitespace characters on lines only containing whitespaces
            see: https://bugs.python.org/issue30754

            And some people set their editors to strip trailing white space.

            But sometimes there is a space on an empty line in the output which will fail the comparison.

            So strip the spaces on empty lines

        :param lines: string of lines to normalise
        :type lines: str

        :return: normalised lines
        """

        return re.sub('^\s+$', '', lines, flags=re.MULTILINE)

    def run_command(self, cmd_to_run, write_to_stdin=None):
        """
        Run a command in shell mode returning stdout, stderr and the returncode.

        :param cmd_to_run: shell command to run
        :type cmd_to_run: str

        :param write_to_stdin: string to put on stdin if not None
        :type write_to_stdin: str | None

        :return: stdout, stderr, returncode
        :rtype: (str, str, int)
        """

        p = subprocess.Popen(
            cmd_to_run, shell=True, cwd=self.CWD,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if write_to_stdin:
            # Python3 compatibility - input has to be bytes
            write_to_stdin = write_to_stdin.encode()

        stdout, stderr = p.communicate(write_to_stdin)

        if isinstance(stdout, bytes):
            # Python 3 compatibility - output will be bytes
            stdout = stdout.decode()
            stderr = stderr.decode()

        return stdout, stderr, p.returncode

    def runPymentAppAndAssertIsExpected(self,
                                        cmd_args, write_to_stdin=None,
                                        expected_stdout='', expected_stderr='', expected_returncode=0,
                                        output_format=None):
        """
        Run pyment with the cmd_args and output_format specified in a shell and assert it's output matches
        the arguments.

        if expected_stdout and expected_stderr is the result of a re.compile() the output will be checked
        re.search().

        :param cmd_args: Extra arguments to pass to pyment - excluding the output_format
        :param write_to_stdin: the input to put on stdin, use None if there's nothing

        :param expected_stdout: Expected string to see on stdout
        :type expected_stdout: str | Pattern[str]

        :param expected_stderr: Expected string to see on stderr
        :type expected_stderr: str | Pattern[str]

        :param expected_returncode: Expected returncode after running pyment
        :param output_format: The output format - it adds the --output option, use None if auto is required

        :return: None
        :raises: Assertion error if the expected rsult is not found
        """

        def assert_output(cmd_to_run, what, got, expected):
            """
            The comparison works as described in the docstring for runPymentAppAndAssertIsExpected

            :param cmd_to_run: full command that was run - used to build an error message
            :param what: The attribute being checked - used for the error message
            :param got: The result from the test
            :param expected: The expected result from the test
            :raises: AssertionError if the expected result was not found
            """
            if isinstance(expected, self.RE_TYPE):
                msg = "Test failed for cmd {}\n{} was expected to match the regex:\n{}\n" \
                      "But this was the output:\n{!r}\n" \
                    .format(cmd_to_run, what, expected, got)
                assert expected.search(got) is not None, msg
            else:
                if isinstance(expected, str):
                    # Turn lines that only have whitespace into single newline lines to workaround textwrap.dedent
                    # behaviour
                    got = self.normalise_empty_lines(got).replace('\r\n', '\n')
                    expected = self.normalise_empty_lines(expected)

                #  repr is used instead of str to make it easier to see newlines and spaces if there's a difference
                msg = "Test failed for cmd {}\n{} was expected to be:\n{!r}\nBut this was the output:\n{!r}\n" \
                    .format(cmd_to_run, what, expected, got)
                assert got == expected, msg

        cmd_to_run = self.CMD_PREFIX.format(cmd_args)

        if output_format:
            cmd_to_run = '{} --output {} '.format(cmd_to_run, output_format)

        stdout, stderr, returncode = self.run_command(cmd_to_run, write_to_stdin)

        assert_output(cmd_to_run, 'stderr', stderr, expected_stderr)
        assert_output(cmd_to_run, 'returncode', returncode, expected_returncode)
        assert_output(cmd_to_run, 'stdout', stdout, expected_stdout)


    @unittest.skipIf(sys.version_info[:2] < (3, 3),
                     'Python version < 3.3')
    def testNoArgs_ge_py33(self):
        # Ensure the app outputs an error if there are no arguments.
        self.runPymentAppAndAssertIsExpected(
            cmd_args="",
            write_to_stdin=None,
            # expected_stderr=re.compile('too few arguments'),
            expected_stderr=re.compile(
                r'usage: pymentapp.py \[-h\] \[-i style\] \[-o style\] \[-q quotes\] \[-f status\] \[-t\].?.?\s{20}\[-c config\] \[-d\] \[-p status\] \[-v\] \[-w\] \[-s\].?.?\s{20}path \[path \.\.\.\].?.?pymentapp\.py: error: the following arguments are required: path',
                re.DOTALL),
            expected_returncode=2
        )

    def testStdinPatchMode(self):
        # Test non overwrite mode when using stdin - which means a patch will be written to stdout
        self.runPymentAppAndAssertIsExpected(
            cmd_args="-",
            write_to_stdin=self.INPUT,
            expected_stdout=self.EXPECTED_PATCH,
            output_format=self.OUTPUT_FORMAT,
        )

    def testRunOnStdinOverwrite(self):
        # Check 'overwrite' mode with stdin.
        # In overwrite mode the output is the new file, not a patch.
        self.runPymentAppAndAssertIsExpected(
            cmd_args="-w -",
            write_to_stdin=self.INPUT,
            expected_stdout=self.EXPECTED_OUTPUT,
            output_format=self.OUTPUT_FORMAT,
        )

    def runPymentAppWithAFileAndAssertIsExpected(self,
                                                 file_contents, cmd_args="", overwrite_mode=False,
                                                 expected_file_contents='', expected_stderr='',expected_stdout='', expected_returncode=0,
                                                 output_format=None):
        """
        Run the pyment app with a file - not stdin.

        A temporary file is created, file_contents is written into it then the test is run.
        The .patch and temporary files are removed at the end of the test.

        :param file_contents: write this into the temporary file
        :param cmd_args: Arguments to pyment - do not put the '-w' argument here - it is trigged by overwrite_mode
        :param overwrite_mode: set to True if in overwrite mode
        :param expected_file_contents: expected result - for a patch file ensure the filename is '-'. The '-'
            is replaced with the patch filename when overwrite_mode is False
        :param expected_stderr: expected output on stderr. You can match on a regex if you pass it the result of
            re.compile('some pattern'). Default is empty string.
        :param expected_stdout: Expected string to see on stdout
        :type expected_stdout: str | Pattern[str]
        :param expected_returncode: Expected return code from pyment. Default is 0.
        :param output_format: If not using auto mode set the output format to this.

        """

        patch_filename = input_filename = ""
        input_file = None

        try:

            # Create the input file
            input_fd, input_filename = tempfile.mkstemp(suffix='.input', text=True)
            input_file = os.fdopen(input_fd, 'w')
            input_file.write(file_contents)
            input_file.close()

            # Get the patch file name so it can be removed if it's created.
            # pyment will create it in the current working directory
            patch_filename = os.path.join(self.CWD, os.path.basename(input_filename) + '.patch')

            cmd_args = "{} {}".format(cmd_args, input_filename)

            if overwrite_mode:
                cmd_args = "{} -w ".format(cmd_args)

            self.runPymentAppAndAssertIsExpected(
                cmd_args=cmd_args,
                expected_stderr=expected_stderr,
                expected_returncode=expected_returncode,
                expected_stdout=expected_stdout,
                write_to_stdin=file_contents,
                output_format=output_format,
            )

            if overwrite_mode:
                with open(input_filename) as f:
                    output = f.read()
            else:
                with open(patch_filename) as f:
                    output = f.read()
                # The expected output will have filenames of '-'  - replace them with the actual filename
                output = re.sub(
                    r'/{}$'.format(os.path.basename(input_filename)),
                    r'/-',
                    output,
                    flags=re.MULTILINE
                )

            normalised_output = self.normalise_empty_lines(output)
            normalised_expected_output = self.normalise_empty_lines(expected_file_contents)

            assert normalised_output == normalised_expected_output, \
                "Output from cmd: {} was:\n{!r}\nnot the expected:\n{!r}" \
                    .format(cmd_args, normalised_output, normalised_expected_output)

        finally:
            if input_filename:
                if input_file:
                    if not input_file.closed:
                        input_file.close()
                os.remove(input_filename)

            if not overwrite_mode:
                if os.path.isfile(patch_filename):
                    os.remove(patch_filename)

    def testOverwriteFilesTheSame(self):
        # Test that the file is correct when the output is the same as the input.
        self.runPymentAppWithAFileAndAssertIsExpected(
            file_contents=self.EXPECTED_OUTPUT,
            expected_file_contents=self.EXPECTED_OUTPUT,
            output_format=self.OUTPUT_FORMAT,
            overwrite_mode=True,

        )

    def testOverwriteFilesDifferent(self):
        # Test the file is overwritten with the correct result
        self.runPymentAppWithAFileAndAssertIsExpected(
            file_contents=self.INPUT,
            expected_file_contents=self.EXPECTED_OUTPUT,
            expected_stdout=re.compile(r"Modified docstrings of elements \(Module, func\) in file.*", re.DOTALL),
            output_format=self.OUTPUT_FORMAT,
            overwrite_mode=True,
        )

    def testPatchFilesTheSame(self):
        # Check the patch file created when the files are the same
        self.runPymentAppWithAFileAndAssertIsExpected(
            file_contents=self.EXPECTED_OUTPUT,
            expected_file_contents=self.PATCH_PREFIX + "\n",
            output_format=self.OUTPUT_FORMAT
        )

    def testPatchFilesDifferent(self):
        # Test the patch file is correct
        self.runPymentAppWithAFileAndAssertIsExpected(
            file_contents=self.INPUT,
            expected_file_contents=self.EXPECTED_PATCH,
            output_format=self.OUTPUT_FORMAT
        )


def main():
    unittest.main()


if __name__ == '__main__':
    main()
