<!-- Modal Revisi Approval -->
<div id="modal_revisi_approval" class="modal" style="padding: 60px;">
    <div class="modal-content">
        <div class="modal-header">
            <h3 class="modal-title">Input Pesan Revisi</h3>
            <button type="button" class="close" data-dismiss="modal">&times;</button>
        </div>
        <form action="action/sent_email_revisi.php" method="post" enctype="multipart/form-data">
            <div class="modal-body" style="padding: 40px 40px 10px 40px;">
                <div>
                    <h4 style="font-size: medium;"><?php echo $nama; ?></h4>
                </div>
                <div style="display: flex; margin-bottom: 20px;"">
                    <input type="hidden" name="selected_dept" value="<?php echo $selected_dept; ?>">
                    <textarea name="pesan_revisi" id="pesan_revisi" cols="50" rows="5"></textarea>
                </div>
            </div>
            <div class="modal-footer" style="padding-top: 24px;">
                <button type="submit" id="modal_sent_btn" class="btn-save" style="width: 150px; margin-right: 20px;">Send Email<br>To ICon</button>
            </div>
        </form>
    </div>
</div>