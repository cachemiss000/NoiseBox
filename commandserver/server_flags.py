from absl import flags

FLAGS = flags.FLAGS

flags.DEFINE_bool("debug", False, "Run the server in debug mode. Provides messy-but-debug-friendly output. "
                                  "Not recommended for end users.")

flags.DEFINE_list('run_versions', default='v1',
                  help='versions to run. Currently supported: [V1]')

flags.DEFINE_string('server_log_level', 'WARN',
                    help='The log level at which the command server should start printing out messages.')

# No good list of built-in log levels, so lets make our own =/
LOG_LEVELS = ['CRITICAL', 'FATAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG']
flags.register_validator('server_log_level',
                         lambda level: level in LOG_LEVELS,
                         "--server_log_level must be one of '%s'" % (LOG_LEVELS,))
