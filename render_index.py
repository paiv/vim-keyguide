#!/usr/bin/env python
import logging
import re
import string
from pathlib import Path


logger = logging.getLogger(Path(__file__).name)


def parse_index_txt(file):
    abc = string.ascii_lowercase
    state = 0
    for line in file:
        consumed = False
        while not consumed:
            consumed = True

            match state:
                case 0:
                    if line.startswith('===='):
                        state = 1
                case 1:
                    num, title = line.split(maxsplit=1)
                    title,*_ = title.split('\t', maxsplit=1)
                    state = 2
                    mode = num.strip().rstrip('.') + '.'
                    subsec = 0
                    yield ((mode, title.strip()), None)
                case 2:
                    if line.startswith('----'):
                        state = 3
                case 3:
                    if line.startswith('===='):
                        state = 1
                    elif line[0] == '|':
                        i = line.index('|', 1)
                        act,*text = line[i+1:].strip().split('\t', maxsplit=1)
                        text = ' '.join(text).strip() if text else ''
                        text = re.sub(r'^[12,\s]+', '', text)
                        state = 4
                    elif line.startswith('\t\t'):
                        act,*text = line.strip().split('\t', maxsplit=1)
                        text = ' '.join(text).strip() if text else ''
                        text = re.sub(r'^[12,\s]+', '', text)
                        state = 4
                    elif line.startswith('commands in '):
                        sid = f'{mode}{abc[subsec]}'
                        subsec += 1
                        stx = line.split('*', maxsplit=1)[0].strip()
                        yield ((sid, stx), None)
                        state = 3
                case 4:
                    if line.startswith('===='):
                        state = 1
                        yield (None, (act, text))
                    elif not line.strip():
                        state = 3
                        yield (None, (act, text))
                    elif line.startswith('\t\t\t'):
                        text += ' ' + (re.sub(r'^[12,\s]+', '', line) if not text else line).strip()
                    elif line[0] == '|' or line.startswith('\t\t'):
                        consumed = False
                        state = 3
                        yield (None, (act, text))
                    else:
                        text += ' ' + (re.sub(r'^[12,\s]+', '', line) if not text else line).strip()
                case 9:
                    if line.startswith('===='):
                        state = 1


_rxcmd = re.compile(r''':\S+|\[[^\]]+\]|{[^}]+}|CTRL-\S+|<[^>]+>|'[^']+'|\w+|\S''')

def tokenize_command(text):
    res = _rxcmd.findall(text)
    return tuple(res)


class Node:
    def __init__(self, value=None, /, label=None):
        self.value = value
        self.label = label
        self.children = dict()

    def child(self, value, /, label=None):
        n = self.children.get(value)
        if n is None:
            n = Node(value)
            self.children[value] = n
        if label is not None:
            n.label = label
        return n


def main(args):
    if args.index:
        index_file = args.index
    else:
        import shutil
        binvim = shutil.which('vim')
        if not binvim:
            raise Exception('file not found: vim')
        sharevim = Path(binvim).parent / '../share/vim'
        for fn in sharevim.glob('**/doc/index.txt'):
            index_file = open(fn.resolve())
            break
        else:
            raise Exception('file not found: doc/index.txt')

    logger.info(f'reading {index_file.name}')

    tri = Node()

    for md,op in parse_index_txt(index_file):
        if md:
            mode,title = md
            tri.child(mode, label=title)
            logger.debug(f'section {mode} {title!r}')
        if op:
            act, desc = op
            act = tokenize_command(act)
            logger.debug(f'{act} {desc!r}')
            n = tri.child(mode)
            for tok in act:
                n = n.child(tok)
            n.label = desc

    def lkey(c):
        return (c.lower(), tuple(map(str.isupper, c)))

    def dump(node, depth, path, file=None):
        if node.label:
            ws = '  ' if depth else f'\n{node.value}'
            l = f'  {node.label}'
            v = ' '.join(path)
            print(f'{ws}{v}{l}', file=file)
        for k in sorted(node.children.keys(), key=lkey):
            c = node.children[k]
            dump(c, depth + 1, path + [c.value], file)
    
    def dump_modes(root, file=None):
        for k in sorted(root.children.keys(), key=lkey):
            c = root.children[k]
            dump(c, 0, list())

    dump_modes(tri)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('index', nargs='?', type=argparse.FileType(), help='vim help index.txt')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.WARN
    logging.basicConfig(level=level)

    main(args)
