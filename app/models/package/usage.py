from datetime import datetime

from ...lib.connection import connection


def record(details):
    """
    Records that a user installed, upgraded or uninstalled a package
    """

    now = datetime.utcnow()
    today = now.date()

    package = details['package']
    ip = details['ip']
    platform = details['platform']
    operation = details['operation']

    if platform not in ['osx', 'linux', 'windows']:
        raise Exception('Invalid platform')

    if operation not in ['install', 'upgrade', 'remove']:
        raise Exception('Invalid operation')

    with connection() as cursor:
        # Record the unique user
        cursor.execute("""
            SELECT
                ip,
                sublime_platform
            FROM
                ips
            WHERE
                ip = %s AND
                sublime_platform = %s
        """, [ip, platform])
        if not cursor.rowcount:
            cursor.execute("""
                INSERT INTO ips (
                    ip,
                    sublime_platform
                ) VALUES (
                    %s,
                    %s
                )
            """, [ip, platform])

        cursor.execute("""
            INSERT INTO usage (
                ip,
                user_agent,
                package,
                operation,
                date_time,
                version,
                old_version,
                package_control_version,
                sublime_platform,
                sublime_version
            ) VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, [
            ip,
            details['user_agent'],
            package,
            operation,
            now,
            details['version'],
            details['old_version'],
            details['package_control_version'],
            platform,
            details['sublime_version']
        ])

        if operation == 'install':
            # Record a unique package install
            increase_unique_installs = False
            cursor.execute("""
                SELECT
                    ip,
                    package,
                    sublime_platform
                FROM
                    unique_package_installs
                WHERE
                    ip = %s AND
                    package = %s AND
                    sublime_platform = %s
            """, [ip, package, platform])
            if not cursor.rowcount:
                increase_unique_installs = True
                cursor.execute("""
                    INSERT INTO unique_package_installs (
                        ip,
                        package,
                        sublime_platform
                    ) VALUES (
                        %s,
                        %s,
                        %s
                    )
                """, [ip, package, platform])

            # Initialize the daily package stats if necessary
            cursor.execute("""
                SELECT
                    date,
                    package
                FROM
                    daily_install_counts
                WHERE
                    date = %s AND
                    package = %s
            """, [today, package])
            if not cursor.rowcount:
                cursor.execute("""
                    INSERT INTO daily_install_counts (
                        date,
                        package
                    ) VALUES (
                        %s,
                        %s
                    )
                """, [today, package])

            # Initialize the package stats if necessary
            cursor.execute("""
                SELECT
                    package
                FROM
                    install_counts
                WHERE
                    package = %s
            """, [package])
            if not cursor.rowcount:
                cursor.execute("""
                    INSERT INTO install_counts (
                        package
                    ) VALUES (
                        %s
                    )
                """, [package])

            # Update the various install counts
            if increase_unique_installs:
                cursor.execute("""
                    UPDATE
                        install_counts
                    SET
                        unique_installs = unique_installs + 1,
                        """ + platform + """_unique_installs = """ + platform + """_unique_installs + 1
                    WHERE
                        package = %s
                """, [package])

            cursor.execute("""
                UPDATE
                    install_counts
                SET
                    installs = installs + 1,
                    """ + platform + """_installs = """ + platform + """_installs + 1
                WHERE
                    package = %s
            """, [package])

            cursor.execute("""
                UPDATE
                    daily_install_counts
                SET
                    installs = installs + 1,
                    """ + platform + """_installs = """ + platform + """_installs + 1
                WHERE
                    package = %s AND
                    date = %s
            """, [package, today])
