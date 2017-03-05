import sublime
import sublime_plugin

from functools import reduce

COL_MIN, ROW_MIN, COL_MAX, ROW_MAX = 0,1,2,3
LEFT,ABOVE,RIGHT,BELOW = 0,1,2,3

directions = {'left' : LEFT, 'above' : ABOVE, 'right' : RIGHT, 'below' : BELOW}

def opposite(direction):
    return (direction-2)%4


def increment_if_greater_equal(number,threshold):
    return number + 1 if number >= threshold else number


def push_cols(cells,threshold):
    return [[ increment_if_greater_equal(col_min,threshold), row_min,
              increment_if_greater_equal(col_max,threshold), row_max ]
            for col_min,row_min,col_max,row_max in cells]


def push_rows(cells,threshold):
    return [[ col_min, increment_if_greater_equal(row_min,threshold),
              col_max, increment_if_greater_equal(row_max,threshold) ]
            for col_min,row_min,col_max,row_max in cells]


def decrement_if_greater_equal(number,threshold):
    return number - 1 if number >= threshold else number


def pull_cols(cells,threshold):
    return [[ decrement_if_greater_equal(col_min,threshold), row_min,
              decrement_if_greater_equal(col_max,threshold), row_max ]
            for col_min,row_min,col_max,row_max in cells]


def pull_rows(cells,threshold):
    return [[ col_min, decrement_if_greater_equal(row_min,threshold),
              col_max, decrement_if_greater_equal(row_max,threshold) ]
            for col_min,row_min,col_max,row_max in cells]


def find_adjacente_panels(cells,active):
    act_col_min,act_row_min,act_col_max,act_row_max = active

    #Find left and right
    left = []
    right = []
    above = []
    below = []
    for i,(col_min,row_min,col_max,row_max) in enumerate(cells):
        if row_min >= act_row_min and row_max <= act_row_max:
            if col_max == act_col_min:
                left.append(i)
            elif col_min == act_col_max:
                right.append(i)

        if col_min >= act_col_min and col_max <= act_col_max:
            if row_max == act_row_min:
                above.append(i)
            elif row_min == act_row_max:
                below.append(i)

    return [left,above,right,below]



def find_next_panel(cells, active, direction):

    for i,cell in enumerate(cells):
        if cell[(direction+1)%2] <= active[(direction+1)%2] < cell[((direction+1)%2)+2]:
            if cell[(direction+2)%4] == active[direction]:
                return i

    return None


class LayoutCommand(sublime_plugin.WindowCommand):

    def get_layout(self):
        layout = self.window.get_layout()
        cells = layout["cells"]
        rows = layout["rows"]
        cols = layout["cols"]
        return rows, cols, cells


    def get_axis_values(self, cols, rows, cell):
        col_min = cols[cell[COL_MIN]]
        col_max = cols[cell[COL_MAX]]
        
        row_min = rows[cell[ROW_MIN]]
        row_max = rows[cell[ROW_MAX]]
        return col_min, row_min, col_max, row_max


    def run(self, direction):
        self.move_focus(directions[direction])


    def update_layout(self, rows, cols, cells):
        self.window.set_layout({'cols': cols,'rows': rows,'cells' : cells})


    def move_focus(self, direction):
        rows, cols, cells = self.get_layout()
        current_group = self.window.active_group()
        current_cell = cells[current_group]

        next_panel = find_next_panel(cells,current_cell,direction)
        if next_panel != None:
             self.window.focus_group(next_panel)



class CreatePanelCommand(LayoutCommand):

    def run(self,orientation = 'horizontal'):
        self.create_panel(orientation)


    def create_panel(self, orientation):
        rows, cols, cells = self.get_layout()
        current_group = self.window.active_group()
        old_cell = cells.pop(current_group)

        if orientation == 'horizontal':
            new_division = (cols[old_cell[COL_MIN]] + cols[old_cell[COL_MAX]])/2
            if not new_division in cols:
                cells = push_cols(cells,old_cell[COL_MAX])
                cols.insert(old_cell[COL_MAX],new_division)
                new_cell = [old_cell[COL_MIN]+1, old_cell[ROW_MIN], old_cell[COL_MAX]+1, old_cell[ROW_MAX]]
            else:
                index = cols.index(new_division)
                new_cell = [index, old_cell[ROW_MIN], old_cell[COL_MAX], old_cell[ROW_MAX]]
                old_cell[COL_MAX] = index
            
        elif orientation == 'vertical':
            new_division = (rows[old_cell[ROW_MIN]] + rows[old_cell[ROW_MAX]])/2
            if not new_division in rows:
                cells = push_rows(cells,old_cell[ROW_MAX])
                rows.insert(old_cell[ROW_MAX],new_division)
                new_cell = [old_cell[COL_MIN], old_cell[ROW_MIN]+1, old_cell[COL_MAX], old_cell[ROW_MAX]+1]
            else:
                index = rows.index(new_division)
                new_cell = [old_cell[COL_MIN], index, old_cell[COL_MAX], old_cell[ROW_MAX]]
                old_cell[ROW_MAX] = index
        
        cells.insert(current_group,old_cell)
        cells.append(new_cell)
        print(cells)
        self.update_layout(rows,cols,cells)
        self.window.focus_group(len(cells)-1)


class DestroyPanelCommand(LayoutCommand):

    def run(self,orientation = 'self'):
        self.destroy_panel(orientation)


    def destroy_panel(self, orientation):
        if orientation == 'self':
            self.destroy_active_panel()


    def destroy_active_panel(self):
        rows, cols, cells = self.get_layout()
        current_group = self.window.active_group()
        cur_cell = cells.pop(current_group)

        adjacent_panels = find_adjacente_panels(cells,cur_cell)
        adjacent_size = reduce((lambda x, y:len(y)+x),adjacent_panels,0)

        if adjacent_size == 0:
            self.window.run_command('close_window')
            return
        else:
            priority =  self._destroy_priority(cells,rows,cols,cur_cell)

            for direction in priority:
                if adjacent_panels[direction]:
                    for panel in adjacent_panels[direction]:
                        edge = opposite(direction)
                        cells[panel][edge] = cur_cell[edge]
                    direction_focus = adjacent_panels[direction][0]
                    break

        unused_cols = sorted(self._find_least_used([c[::2] for c in cells],cols,0),reverse = True)
        unused_rows = sorted(self._find_least_used([c[1::2] for c in cells],rows,0),reverse = True)

        cols = [e for i,e in enumerate(cols) if i not in unused_cols]
        rows = [e for i,e in enumerate(rows) if i not in unused_rows]
        for c in unused_cols:
            cells = pull_cols(cells,c)
        for r in unused_rows:
            cells = pull_rows(cells,r)

        self.update_layout(rows,cols,cells)
        self.window.focus_group(direction_focus)


    def _destroy_priority(self, cells, rows,cols,cur_cell):
        col_min, row_min, col_max, row_max = self.get_axis_values(cols, rows, cur_cell)
        
        cell = [col_min,row_min,col_max,row_max]

        horizontal_dir = []

        if col_min > 0.0:
            horizontal_dir.append(LEFT)
        if col_max < 1.0:
            horizontal_dir.append(RIGHT)

        vertical_dir = []

        if row_min > 0.0:
            vertical_dir.append(ABOVE)
        if row_max < 1.0:
            vertical_dir.append(BELOW)

        horizontal = horizontal_dir if self._orient_left(cols,*(cur_cell[::2])) else horizontal_dir[::-1]
        vertical = vertical_dir if self._orient_left(rows,*(cur_cell[1::2])) else vertical_dir[::-1]

        priority = horizontal+vertical if (row_max - row_min) > (col_max - col_min) else  vertical+horizontal

        unused_cols = self._find_least_used([c[::2] for c in cells],cols,1)
        unused_rows = self._find_least_used([c[1::2] for c in cells],rows,1)

        unused_axis = (unused_cols,unused_rows)

        is_unused = [cur_cell[direction] in unused_axis[direction%2] for direction in priority]

        unused_ones = []
        used_ones = []
        for direction,unused in zip(priority,is_unused):
            if unused:
                unused_ones.append(direction)
            else:
                used_ones.append(direction)

        return unused_ones+used_ones


    def _find_least_used(self, cells,axis, threshold):
        used = [0]*len(axis)

        for c in cells:
            used[c[0]]+=1
            used[c[1]]+=1

        return [i+1 for i,x in enumerate(used[1:-1]) if x <= threshold]


    def _orient_left(self, axis,min_edge,max_edge):
        for a,b in zip(axis[:min_edge][::-1], axis[max_edge+1:]):
            if (axis[min_edge]-a) < (b-axis[max_edge]):
                return True
            elif (b-axis[max_edge]) < (axis[min_edge]-a):
                return False
        return False if min_edge > (len(axis)-max_edge-1) else True
