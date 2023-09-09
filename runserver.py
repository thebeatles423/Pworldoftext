import sqlite3
import os
import prompt

# Additional import statements go here

_static = {}
_staticPath = "./program/html/static/"
_staticURL = "static/"

_template = {}
_templatePath = "./program/html/templates/"

SETTINGS = {}
DATABASE_PATH = SETTINGS['DATABASE_PATH']
CHECK_STATE_PATH = SETTINGS['CHECK_STATE_PATH']
LOG_PATH = SETTINGS['LOG_PATH']

down = False
message = ""
date = "No date yet..."


def is_down(a=None):
    if not a:
        return down
    elif a:
        return [message, date]


prompt.message = ""
prompt.delimiter = ""
prompt.colors = False


prompt_account_properties = {
    'properties': {
        'username': {
            'message': 'Username: '
        },
        'password': {
            'description': 'Password: ',
            'replace': '*',
            'hidden': True
        },
        'confirmpw': {
            'description': 'Password (again): ',
            'replace': '*',
            'hidden': True
        }
    }
}

prompt_account_yesno = {
    'properties': {
        'yes_no_account': {
            'message': "You just installed the server, which means you don't have any superusers defined.\n"
                       "Would you like to create one now? (yes/no):"
        }
    }
}

command_props = {
    'properties': {
        'command': {
            'message': ">"
        }
    }
}


def log_problem(err):
    if SETTINGS['error_log']:
        try:
            errs = err
            if not isinstance(errs, str):
                errs = str(errs.stack)
            errs = json.dumps(errs)
            err = "[" + errs + ", " + str(time.time()) + "]\r\n"
            with open(LOG_PATH, "a") as log_file:
                log_file.write(err)
        except Exception as e:
            print(e)


def create_tables(list, callback):
    global id_0
    grp = id_0
    id_0 += 1
    if grp not in create_tables_grps:
        create_tables_grps[grp] = 0
    for i in range(len(list)):
        sql = list[i]
        args = None
        eachFC = None
        if isinstance(sql, list):
            eachFC = sql[2]
            args = sql[1]
            sql = sql[0]
        OPT = ["run", sql, lambda: create_tables_grps[grp] + 1, args]
        OPT.append(eachFC)
        exec_sql(*OPT)

    if create_tables_grps[grp] >= len(list):
        del create_tables_grps[grp]
        callback()


def return_tables(list, callback):
    global id_0
    grp = id_0
    id_0 += 1
    data = []
    if grp not in return_tables_grps:
        return_tables_grps[grp] = 0
    for i in range(len(list)):
        sql = list[i]
        args = None
        eachFC = None
        if isinstance(sql, list):
            eachFC = sql[2]
            args = sql[1]
            sql = sql[0]
        OPT = ["get", sql, lambda a, b: (return_tables_grps[grp] + 1, data.append(b)), args]
        OPT.append(eachFC)
        exec_sql(*OPT)

    if return_tables_grps[grp] >= len(list):
        del return_tables_grps[grp]
        callback(data)


def escape_sql(s):
    s = s.replace("'", "''")
    s = s.replace('"', '""')
    return s


def pad_string(s, count, character):
    CS = character * count
    SJ = CS + s
    return SJ[-count:]


def make_date(tst):
    date = datetime.datetime.fromtimestamp(tst / 1000.0)
    compile_date = date.strftime("%Y-%m-%d %H:%M:%S.%f")
    return compile_date


def reverse_date(s):
    return int(time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S.%f")) * 1000)


def pass_func(err, result):
    err = False
    if result['password'] != result['confirmpw']:
        print("Error: Your passwords didn't match.")
        err = True
        prompt.get(prompt_account_properties, pass_func)
    elif len(result['password']) > 128:
        print("The password is too long. It must be 128 characters or less.")
        err = True
        prompt.get(prompt_account_properties, pass_func)

    if len(result['username']) > 30:
        print("The username must be 30 characters or less.")
        err = True
        prompt.get(prompt_account_properties, pass_func)
    elif len(result['username']) < 1:
        print("The username is too short")
        err = True
        prompt.get(prompt_account_properties, pass_func)
    elif not re.match(r'^\w*$', result['username']):
        print("The username must contain the following characters: a-z A-Z 0-9 _")
        err = True
        prompt.get(prompt_account_properties, pass_func)

    if not err:
        Date_ = int(time.time() * 1000)
        passHash = encrypt_hash(result['password'])
        exec_sql("run", "INSERT INTO auth_user VALUES(null, ?, '', '', '', ?, 1, 1, 1, ?, ?)",
                 lambda a, b: (print("Superuser created successfully.\n"), run_server()), [result["username"],
                                                                                             passHash, Date_, Date_])


def yes_no_account(err, result):
    re = result['yes_no_account']
    if re.upper() == "YES":
        prompt.get(prompt_account_properties, pass_func)
    elif re.upper() == "NO":
        run_server()
    else:
        print("Please enter either \"yes\" or \"no\" (not case sensitive):")
        prompt.get(prompt_account_yesno, yes_no_account)


def exec_sql(mtd, sql, clbk, args=None, each_fc=None):
    ar = [mtd, sql, clbk, args, each_fc]
    queue.append(ar)
    if not to_check:
        check_queue()
        to_check = True


def check_queue():
    if len(queue) == 0:
        to_check = False
        return
    mtd = queue[0][0]
    sql = queue[0][1]
    clbk = queue[0][2]
    args = queue[0][3]
    each_fc = queue[0][4]

    in_memory = False

    if mtd[0] == "_":
        in_memory = True
        mtd = mtd[1:]

    if mtd == "run" or mtd == "each" or mtd == "get" or mtd == "all":
        OPT = [sql]
        if args:
            OPT.append(args)
        if mtd == "each" and not each_fc:
            OPT.append(lambda: None)
        if mtd == "each" and each_fc:
            OPT.append(lambda a, b: (each_fc(a, b) if not a else log_problem(
                "SQL error: " + json.dumps(a) + " with args: " + json.dumps(args) + " using SQL: " + json.dumps(
                    sql))))
        OPT.append(lambda a, b: (queue.pop(0), check_queue(), clbk(a, b) if not a else log_problem(
            "SQL error: " + json.dumps(a) + " with args: " + json.dumps(args) + " using SQL: " + json.dumps(sql))))
        try:
            if not in_memory:
                dtB[mtd](*OPT)
            if in_memory:
                QTB[mtd](*OPT)
        except Exception as e:
            log_problem(e)
    else:
        queue.pop(0)
        check_queue()


def run_server():
    server.begin()
    prompt.get(command_props, comm_fc)


def comm_fc(err, res):
    js = res['command']
    if js != "rs" and not js.startswith("end") and js != "start":
        try:
            res = eval(js)
            print(res)
        except Exception as e:
            print(e)
    try:
        if js.startswith("end"):
            sp = js[4:]
            down = True
            message = sp
            date = datetime.datetime.now()
        if js == "start":
            down = False
    except Exception as e:
        print(e)
    prompt.get(command_props, comm_fc)


pw_encryption = "sha512WithRSAEncryption"


def encrypt_hash(pass_, salt=None):
    if not salt:
        salt = os.urandom(10).hex()
    hsh = hashlib.pbkdf2_hmac(pw_encryption, pass_.encode(), bytes.fromhex(salt), 100000)
    hash_ = pw_encryption + "$" + salt + "$" + hsh.hex()
    return hash_


def check_hash(hash_, pass_):
    if not isinstance(hash_, str):
        return False
    hash_ = hash_.split("$")
    if len(hash_) != 3:
        return False
    if not isinstance(pass_, str):
        return False
    return encrypt_hash(pass_, hash_[1]) == "$".join(hash_)


def extr():
    fs = None
    try:
        with open(CHECK_STATE_PATH, "r") as file:
            data = file.read()
    except Exception as a:
        print("Setting up default tables...")
        create_tables(default_tables, lambda: (
            print("Tables successfully set up."), open(LOG_PATH, "w").close(), open(CHECK_STATE_PATH, "w").close(),
            prompt.start(), prompt.get(prompt_account_yesno, yes_no_account)))

    if not fs:
        run_server()
