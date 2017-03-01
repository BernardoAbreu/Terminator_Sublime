import sublime
import sublime_plugin

COL_MIN, ROW_MIN, COL_MAX, ROW_MAX = 0,1,2,3

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


class LayoutCommand(sublime_plugin.WindowCommand):

    def get_layout(self):
        layout = self.window.get_layout()
        cells = layout["cells"]
        rows = layout["rows"]
        cols = layout["cols"]
        return rows, cols, cells


    def run(self,orientation = 'horizontal'):

        self.create_panel(orientation)


    def update_layout(self, rows, cols, cells):
        self.window.set_layout({'cols': cols,'rows': rows,'cells' : cells})


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
                new_cell = [index, old_cell[ROW_MIN], index, old_cell[ROW_MAX]]
                old_cell[3] = index
            
        elif orientation == 'vertical':
            new_division = (rows[old_cell[ROW_MIN]] + rows[old_cell[ROW_MAX]])/2
            if not new_division in rows:
                cells = push_rows(cells,old_cell[ROW_MAX])
                rows.insert(old_cell[ROW_MAX],new_division)
                new_cell = [old_cell[COL_MIN], old_cell[ROW_MIN]+1, old_cell[COL_MAX], old_cell[ROW_MAX]+1]
            else:
                index = rows.index(new_division)
                new_cell = [old_cell[COL_MIN], index, old_cell[COL_MAX], old_cell[ROW_MAX]]
                old_cell[3] = index
        
        cells.insert(current_group,old_cell)
        cells.append(new_cell)

        self.update_layout(rows,cols,cells)
        self.window.focus_group(len(cells)-1)